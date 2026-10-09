# -*- coding: utf-8 -*-
r"""
Output-algo: 从手表(自动扫描所有非系统盘)的 algo 文件夹中剪切日志到本地，并按测试分组整理。
- 盘符扫描：自动扫描 E~Z 所有盘符（排除 C 系统盘、D 输出/源盘）
  - 新固件下手表盘符可能是 E/F/G/... 任意一个，不再硬编码
- 剪切过程：使用 shutil.move（稳定可靠）
- 分组整理：先按功能名分类，再按序号 0 的出现切分测试
  - 文件夹命名：{功能}_{时间}_测试{N}
  - 时间取自该测试序号 0 文件的时间戳，自动转为北京时间格式
"""

import os
import re
import shutil
import time
import tkinter as tk
from tkinter import messagebox
from datetime import datetime, timezone, timedelta


# 需要排除的盘符（C=系统盘, D=源文件所在盘/输出盘）
EXCLUDE_DRIVES = {'C', 'D'}
# 扫描范围: E ~ Z 全部盘符（去掉排除项）
SCAN_DRIVES = [chr(c) for c in range(ord('E'), ord('Z') + 1) if chr(c) not in EXCLUDE_DRIVES]

# 输出根目录
OUTPUT_BASE = r'D:\Suunto\Output-algo'

# 北京时间 UTC+8
CST = timezone(timedelta(hours=8))


# ============================================================
# 1. 查找手表 algo 文件夹
# ============================================================

def find_algo_folder():
    found_drive = None
    for drive in SCAN_DRIVES:
        drive_path = f'{drive}:\\'
        if os.path.exists(drive_path) and os.path.isdir(drive_path):
            found_drive = drive
            algo_path = os.path.join(drive_path, 'algo')
            if os.path.exists(algo_path) and os.path.isdir(algo_path):
                return drive, algo_path
    return found_drive, None


# ============================================================
# 2. 文件名解析 & 时间戳转换
# ============================================================

NUM_RE = re.compile(r'^\d+$')


def parse_filename(filename):
    """
    解析命名为 功能_时间戳_序号.ext 的文件名。
    返回: (功能名, 时间戳原始字符串, 序号int, 扩展名)
    解析失败返回 None
    """
    stem, ext = os.path.splitext(filename)
    parts = stem.split('_')
    if len(parts) < 3:
        return None
    if not NUM_RE.match(parts[-1]):
        return None
    if not NUM_RE.match(parts[-2]):
        return None
    seq = int(parts[-1])
    ts_raw = parts[-2]
    feature = '_'.join(parts[:-2])
    if not feature:
        return None
    return feature, ts_raw, seq, ext


def timestamp_to_cst_str(ts_raw):
    """把时间戳原始字符串转成北京时间 YYYYMMDD_HHMMSS 格式。"""
    s = str(ts_raw).strip()
    dt = None
    if NUM_RE.match(s):
        n = len(s)
        try:
            if n == 10:
                dt = datetime.fromtimestamp(int(s), CST)
            elif n == 13:
                dt = datetime.fromtimestamp(int(s) / 1000.0, CST)
            elif n == 14:
                dt = datetime.strptime(s, '%Y%m%d%H%M%S').replace(tzinfo=CST)
            elif n == 17:
                dt = datetime.strptime(s, '%Y%m%d%H%M%S%f').replace(tzinfo=CST)
            elif 8 <= n <= 9:
                dt = datetime.fromtimestamp(int(s), CST)
            elif 10 < n < 13:
                dt = datetime.fromtimestamp(int(s) / (10 ** (n - 10)), CST)
            elif 14 < n < 17:
                dt = datetime.strptime(s[:14], '%Y%m%d%H%M%S').replace(tzinfo=CST)
        except Exception:
            dt = None

    if dt is None:
        safe = s.replace('/', '-').replace(':', '-').replace('\\', '-')
        for ch in '*?"<>|':
            safe = safe.replace(ch, '_')
        return safe

    return dt.strftime('%Y%m%d_%H%M%S')


# ============================================================
# 3. 按测试分组整理 algo 文件夹内容
# ============================================================

INVALID_DIR_CHARS = '<>:"/\\|?*'


def safe_dirname(s):
    for ch in INVALID_DIR_CHARS:
        s = s.replace(ch, '_')
    return s.strip().rstrip('.') or '_'


def organize_by_tests(algo_dir, output_base):
    """
    将 algo_dir 中的文件按「先功能分类、再按序号切分测试」整理到 output_base 下。
    """
    # 1. 收集并解析所有文件
    parsed_files = []
    unclassified = []
    for name in sorted(os.listdir(algo_dir)):
        full = os.path.join(algo_dir, name)
        if not os.path.isfile(full):
            continue
        parsed = parse_filename(name)
        if parsed is None:
            unclassified.append(name)
            continue
        feature, ts_raw, seq, ext = parsed
        parsed_files.append((name, full, feature, ts_raw, seq))

    if not parsed_files:
        return 0, 0, unclassified, [], []

    # 2. 按功能分桶
    by_feature = {}
    for item in parsed_files:
        feature = item[2]
        by_feature.setdefault(feature, []).append(item)

    # 3. 每个功能内排序（按文件名字典序，保证序号递增）
    for feature in by_feature:
        by_feature[feature].sort(key=lambda x: x[0])

    total_groups = 0
    moved_count = 0
    errors = []
    test_folders_created = []
    misfire_files = []  # 误触的文件（单独序号0，没有后续文件）

    for feature, items in by_feature.items():
        # 4. 按序号 0 切分测试
        tests = []
        current = []
        for it in items:
            seq = it[4]
            if seq == 0:
                if current:
                    tests.append(current)
                current = [it]
            else:
                current.append(it)
        if current:
            tests.append(current)

        # 5. 识别误触：只有1个文件（序号0）且后面还有其他测试组
        #    判定为误触，不建立文件夹，文件单独留在 algo 根目录
        #    真正的测试从 1 重新计数
        total_tests = len(tests)
        real_test_idx = 0
        for idx, test_items in enumerate(tests, start=1):
            is_misfire = (len(test_items) == 1) and (idx < total_tests)

            if is_misfire:
                # 误触：记录文件名，不建立文件夹，文件留在 algo 根目录
                misfire_name = test_items[0][0]
                misfire_files.append(misfire_name)
                errors.append(f"检测到误触: {misfire_name}（单独序号0，已跳过）")
                continue

            real_test_idx += 1

            seq0_items = [x for x in test_items if x[4] == 0]
            if seq0_items:
                _, _, _, ts_raw_0, _ = seq0_items[0]
            else:
                # 没有序号 0 的测试，跳过（无法确定时间戳）
                errors.append(f"功能 {feature} 的第 {real_test_idx} 组无序号0文件，已跳过")
                continue

            time_str = timestamp_to_cst_str(ts_raw_0)
            folder_name = safe_dirname(f"{feature}_{time_str}_测试{real_test_idx}")
            folder_path = os.path.join(output_base, folder_name)

            try:
                os.makedirs(folder_path, exist_ok=True)
            except Exception as e:
                errors.append(f"创建文件夹 {folder_name} 失败: {e}")
                continue

            for (name, full, feat, ts_raw, seq) in test_items:
                dst = os.path.join(folder_path, name)
                try:
                    if os.path.exists(dst):
                        base, ext2 = os.path.splitext(name)
                        i = 1
                        while True:
                            new_name = f"{base}_{i}{ext2}"
                            dst = os.path.join(folder_path, new_name)
                            if not os.path.exists(dst):
                                break
                            i += 1
                    # 重试机制：文件可能被短暂占用
                    for attempt in range(3):
                        try:
                            shutil.move(full, dst)
                            moved_count += 1
                            break
                        except PermissionError:
                            if attempt < 2:
                                time.sleep(0.5)
                            else:
                                errors.append(f"移动 {name} -> {folder_name} 失败: 文件被占用")
                        except Exception as e:
                            errors.append(f"移动 {name} -> {folder_name} 失败: {e}")
                            break
                except Exception as e:
                    errors.append(f"移动 {name} -> {folder_name} 失败: {e}")

            total_groups += 1
            test_folders_created.append(folder_name)

    return total_groups, moved_count, unclassified, errors, test_folders_created, misfire_files


# ============================================================
# 4. 主流程
# ============================================================

def main():
    root = tk.Tk()
    root.withdraw()

    drive, algo_path = find_algo_folder()

    # 情况 1: 未检测到任何目标盘符
    if drive is None:
        messagebox.showerror("错误", "U盘未连接成功")
        return

    # 情况 2: 检测到盘符但未找到 algo 文件夹
    if algo_path is None:
        messagebox.showerror("错误", f"未检测到 algo 文件夹（扫描盘符 {drive}:）")
        return

    # 准备目标目录
    os.makedirs(OUTPUT_BASE, exist_ok=True)
    dest_algo = os.path.join(OUTPUT_BASE, 'algo')

    # 检查源 algo 是否为空
    src_entries = os.listdir(algo_path) if os.path.exists(algo_path) else []
    if not src_entries:
        messagebox.showinfo("提示", f"手表 {drive}:\\algo 文件夹是空的，无需传输。")
        return

    # 如果已存在旧的 algo 文件夹，重命名为带时间戳的备份
    if os.path.exists(dest_algo):
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_folder = os.path.join(OUTPUT_BASE, f'algo_{timestamp}')
        try:
            shutil.move(dest_algo, backup_folder)
        except Exception as e:
            if not messagebox.askyesno(
                "警告",
                f"备份旧 algo 文件夹失败:\n{e}\n\n是否仍然继续？"
            ):
                return

    # ---- 步骤 1: 剪切整个 algo 文件夹 ----
    # 把 E:\algo 整个剪切到 D:\Suunto\Output-algo\ 下
    # 结果：D:\Suunto\Output-algo\algo 包含原 E:\algo 的所有内容
    src_algo_parent = os.path.dirname(algo_path)  # E:\ 或 I:\
    algo_folder_name = os.path.basename(algo_path)  # algo

    dest_algo_path = os.path.join(OUTPUT_BASE, algo_folder_name)

    # 如果目标 algo 已经因为备份被移走了，直接剪切
    try:
        shutil.move(algo_path, dest_algo_path)
    except Exception as e:
        # 剪切失败，尝试复制
        try:
            shutil.copytree(algo_path, dest_algo_path)
            # 复制成功后删除源
            shutil.rmtree(algo_path, ignore_errors=True)
        except Exception as e2:
            messagebox.showerror(
                "剪切失败",
                f"无法将 {algo_path} 剪切到:\n{dest_algo_path}\n\n错误: {e}\n\n复制备选也失败: {e2}"
            )
            return

    # 剪切后验证
    if not os.path.exists(dest_algo_path):
        messagebox.showerror(
            "剪切失败",
            f"剪切操作后，目标位置未找到 algo 文件夹:\n{dest_algo_path}"
        )
        return

    dest_files_after = [n for n in os.listdir(dest_algo_path) if os.path.isfile(os.path.join(dest_algo_path, n))]

    if not dest_files_after:
        messagebox.showerror(
            "剪切异常",
            f"剪切成功，但目标 algo 文件夹没有任何文件。"
        )
        return

    # ---- 步骤 2: 按测试分组整理（测试文件夹生成在 algo 文件夹内部）----
    try:
        total_groups, moved_count, unclassified, errors, folders, misfire_files = organize_by_tests(
            dest_algo_path, dest_algo_path
        )
    except Exception as e:
        messagebox.showerror(
            "分组整理失败",
            f"整理过程出现异常:\n{e}\n\n日志已保存在:\n{dest_algo_path}"
        )
        return

    # 如果一个测试文件夹都没生成
    if total_groups == 0:
        sample = "\n".join(dest_files_after[:10])
        messagebox.showwarning(
            "未生成任何测试文件夹",
            f"剪切成功（algo 里有 {len(dest_files_after)} 个文件），"
            f"但没有识别出符合「功能_时间戳_序号」格式的文件，或没有序号0的文件。\n\n"
            f"algo 里的文件名示例:\n{sample}\n\n"
            f"请确认文件名格式是否为: 功能_时间戳_序号.扩展名\n"
            f"其中时间戳和序号都必须是纯数字。"
        )
        return

    # ---- 结果提示 ----
    msg_lines = []
    msg_lines.append(f"剪切完成（源盘 {drive}:），已按测试分组整理。")
    msg_lines.append(f"")
    msg_lines.append(f"生成测试组数: {total_groups}")
    msg_lines.append(f"成功移动文件数: {moved_count}")
    if misfire_files:
        msg_lines.append(f"误触文件数: {len(misfire_files)}（保留在 algo 根目录）")
    if total_groups > 0:
        msg_lines.append(f"")
        msg_lines.append(f"生成的测试文件夹:")
        for fn in folders[:30]:
            msg_lines.append(f"  - {fn}")
        if len(folders) > 30:
            msg_lines.append(f"  ... 其余 {len(folders) - 30} 个省略")
    if misfire_files:
        msg_lines.append(f"")
        msg_lines.append(f"误触文件（单独留在 algo 根目录）:")
        for name in misfire_files[:10]:
            msg_lines.append(f"  - {name}")
    if unclassified:
        msg_lines.append(f"")
        msg_lines.append(f"未识别命名格式，保留在 algo 文件夹中 ({len(unclassified)} 个):")
        for name in unclassified[:10]:
            msg_lines.append(f"  - {name}")
    if errors:
        msg_lines.append(f"")
        msg_lines.append(f"提示 ({len(errors)} 条):")
        for e in errors[:10]:
            msg_lines.append(f"  - {e}")

    messagebox.showinfo("完成", "\n".join(msg_lines))


if __name__ == '__main__':
    main()
