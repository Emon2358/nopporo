import os
import shutil
import subprocess
import tempfile
import zipfile

def create_nopporo_exe(path):
    # ASCIIアートとメッセージを含む nopporo.exe の内容を作成
    ascii_art = r"""
   
                                            .....-+***********+-.....
                                        ....-***********************-....
                                     ....-*****************************=....
                                     .:+*********************************+:
                                   ..+*************************************+..
                                 ..=*****************************************=..
                              ....*********************************************....
                              ...***********************************************...
                              ..*********+==************************+=+**********..
                              .*******+.    ..:******************:... ...+********.
                            ..-******+..       .****************..       .=*******-..
                            ..*******-..       .***************+..       .:********..
                            .-*******+..       .****************..       .+********-.
                            .=********+.... ..-******************-... ...+*********=.
                            .+***********+++************************+++************+.
                            .+**********************++*****+***********************+.
                            .=**********************.+*****.+**********************=.
                            .-********************+..+*****..**********************-.
                            ..********************...+*****  .*********************..
                            ..-******************.  .+*****  ..*******************-..
                            ...*****************.....+*****....:******************...
                              ..*************************************************..
                              ...***********************************************...
                                 .*********************************************.
                                   -.........................................-
                                   ..-====-.+====::====-.=====:.=====.-====-..
                                    .=****=.=****.-****+.*****:.+***+.=****=.
:+++++++++++++++++++++++=:...       .=****=..***:.-****+.*****:..***..=****=.          ..:=+++++++=.
  .+***********************+...    ..........+**.................+*+..........    .....=********-..
  ...:************************=...............*=.................:*-.........   ....=********=.....
    ....-************************-..        ..=...             ...=..           .=********+...
         ..+************************..      ...                   ...      ...:*********....
            .:************************=....                              ...*********:.
              ..-************************:...                       .....+********-...
              .....=***********************+:.....                ....=********=.....
                   ...+***********************=...                .=********=...
                     ...:************************-..         ...=********+:...
                     ......-***********************+:....  ..-*********:...
                          ....=***********************+...:*********:....
                            .....********************=..+********-...
                                 ..-**************+..+********=...
                                   ...+********+..=***********-...
                                 ...-*******+:.-*****************:...
                            .....-********-..**********************+:....
                            ..:********-... ..:+**********************=..
                          .:+*******=...       ..-***********************=....
                     ....+*******=......       .....=***********************-...
                ......+*******+.....              .....************************:....
              .....=********:....                     ...:***********************+.....
              ..=********:...                           ....=***********************=..
         ....-********-...                                   ..+***********************-....
       ...-********=....                                     ....-+***********************-...
  .....-********=....                                          .....-***********************+:.....
  ..:********+...                                                   ...+***********************+...
..+********...                                                        ...:************************=.
    """
    message = "created by Emon support by nopporo"
    content = ascii_art + "\n" + message + "\n"
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

def get_partition_offset(image_path):
    """
    parted を使って、ディスクイメージ内の最初のパーティションの開始オフセット（バイト単位）を取得する。
    """
    result = subprocess.run(["parted", "-s", image_path, "unit", "B", "print"],
                            capture_output=True, text=True)
    if result.returncode != 0:
        print("parted command failed:", result.stderr)
        return None

    for line in result.stdout.splitlines():
        line = line.strip()
        # 先頭が数字ならパーティション情報とみなす
        if line and line[0].isdigit():
            parts = line.split()
            if len(parts) >= 2:
                offset_str = parts[1]
                if offset_str.endswith("B"):
                    offset_str = offset_str[:-1]
                try:
                    offset = int(offset_str)
                    return offset
                except Exception as e:
                    print("Error parsing offset:", e)
                    continue
    return None

def mount_and_copy_with_kpartx(output_hdi, src_file, dst_filename):
    """
    まず kpartx を用いてパーティションマッピングを試み、マッピングが得られた場合はそのパーティションをマウントしてコピーする。
    マッピングが得られなかった場合は、parted でオフセットを取得し、-o loop,offset=... オプションで直接マウントする。
    """
    # ループデバイスのセットアップ
    losetup_proc = subprocess.run(
        ["sudo", "losetup", "-f", "--show", output_hdi],
        capture_output=True, text=True
    )
    if losetup_proc.returncode != 0:
        print("Error setting up loop device:", losetup_proc.stderr)
        return False

    loop_dev = losetup_proc.stdout.strip()
    print("Loop device assigned:", loop_dev)

    # kpartx でパーティションマッピングを試行
    kpartx_proc = subprocess.run(
        ["sudo", "kpartx", "-av", loop_dev],
        capture_output=True, text=True
    )
    partition_mapped = False
    mapped_partition = None
    for line in kpartx_proc.stdout.splitlines():
        parts = line.split()
        # 例: "add map loop0p1 (254:0): ..."
        if len(parts) >= 3 and parts[0] == "add" and "map" in parts[1]:
            mapped_partition = f"/dev/mapper/{parts[1]}"
            partition_mapped = True
            break

    if partition_mapped:
        print("Mapped partition device:", mapped_partition)
        # マウント処理（通常の方法）
        mount_dir = tempfile.mkdtemp(prefix="hdi_mount_")
        mounted = False
        try:
            # 自動検出
            print(f"Trying to mount {mapped_partition} on {mount_dir} without specifying fs type...")
            cmd = ["sudo", "mount", mapped_partition, mount_dir]
            ret = subprocess.run(cmd, capture_output=True, text=True)
            if ret.returncode == 0:
                print("Mounted without specifying fs type.")
                mounted = True
            else:
                print("Auto mount failed:", ret.stderr)
                for fs_type in ["vfat", "msdos", "ntfs", "ext2", "ext3", "ext4", "iso9660"]:
                    print(f"Trying to mount {mapped_partition} on {mount_dir} as {fs_type}...")
                    cmd = ["sudo", "mount", "-t", fs_type, mapped_partition, mount_dir]
                    ret = subprocess.run(cmd, capture_output=True, text=True)
                    if ret.returncode == 0:
                        print(f"Mounted with filesystem type {fs_type}.")
                        mounted = True
                        break
                    else:
                        print(f"Mount attempt with fs type {fs_type} failed: {ret.stderr}")
            if not mounted:
                print("All mount attempts failed.")
                return False

            # ファイルコピー
            dst_path = os.path.join(mount_dir, dst_filename)
            ret = subprocess.run(["sudo", "cp", src_file, dst_path],
                                 capture_output=True, text=True)
            if ret.returncode != 0:
                print("Error copying file to mounted image:", ret.stderr)
                return False
            print("File copied successfully to", dst_path)
        finally:
            subprocess.run(["sudo", "umount", mount_dir])
            shutil.rmtree(mount_dir)
            subprocess.run(["sudo", "kpartx", "-dv", loop_dev],
                           capture_output=True, text=True)
            subprocess.run(["sudo", "losetup", "-d", loop_dev],
                           capture_output=True, text=True)
        return True
    else:
        print("No partition mapping found.")
        # 既存のループデバイスは不要なので解放
        subprocess.run(["sudo", "kpartx", "-dv", loop_dev],
                       capture_output=True, text=True)
        subprocess.run(["sudo", "losetup", "-d", loop_dev],
                       capture_output=True, text=True)
        # parted を利用してパーティション開始オフセットを取得
        offset = get_partition_offset(output_hdi)
        if offset is None:
            print("Failed to determine partition offset using parted.")
            return False
        else:
            print(f"Determined partition offset: {offset} bytes.")
            mount_dir = tempfile.mkdtemp(prefix="hdi_mount_")
            cmd = ["sudo", "mount", "-o", f"loop,offset={offset}", output_hdi, mount_dir]
            ret = subprocess.run(cmd, capture_output=True, text=True)
            if ret.returncode != 0:
                print("Mount with offset failed:", ret.stderr)
                shutil.rmtree(mount_dir)
                return False
            else:
                print(f"Mounted with partition offset {offset}.")
                # ファイルコピー
                dst_path = os.path.join(mount_dir, dst_filename)
                ret = subprocess.run(["sudo", "cp", src_file, dst_path],
                                     capture_output=True, text=True)
                if ret.returncode != 0:
                    print("Error copying file to mounted image:", ret.stderr)
                    subprocess.run(["sudo", "umount", mount_dir])
                    shutil.rmtree(mount_dir)
                    return False
                print("File copied successfully to", dst_path)
                subprocess.run(["sudo", "umount", mount_dir])
                shutil.rmtree(mount_dir)
                return True

def process_hdi(hdi_path, output_hdi):
    # オリジナルのHDIファイルをバックアップとしてコピー
    shutil.copy2(hdi_path, output_hdi)

    # 作業用ディレクトリに nopporo.exe を作成
    exe_filename = "nopporo.exe"
    create_nopporo_exe(exe_filename)

    # マウント＋コピーによる注入を試みる
    if not mount_and_copy_with_kpartx(output_hdi, exe_filename, "nopporo.exe"):
        print("Injection via mount failed. Falling back to appending nopporo.exe to the disk image.")
        try:
            with open(exe_filename, "rb") as f_exe:
                exe_data = f_exe.read()
            with open(output_hdi, "ab") as f_hdi:
                f_hdi.write(exe_data)
            print("Successfully appended nopporo.exe to the disk image.")
        except Exception as e:
            print("Error appending nopporo.exe:", e)
    else:
        print("Successfully injected nopporo.exe into", output_hdi)

    # 一時ファイルの削除
    if os.path.exists(exe_filename):
        os.remove(exe_filename)

    # HDI イメージをZIP圧縮（最大圧縮）して保存
    final_name = "disk_modified_compressed.hdi.zip"
    with zipfile.ZipFile(final_name, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zipf:
        zipf.write(output_hdi, arcname=os.path.basename(output_hdi))
    print("Compressed disk image saved as", final_name)

if __name__ == "__main__":
    input_hdi = "disk.hdi"
    output_hdi = "disk_modified.hdi"
    if not os.path.exists(input_hdi):
        print(f"Error: Input HDI file '{input_hdi}' not found.")
        exit(1)
    process_hdi(input_hdi, output_hdi)
