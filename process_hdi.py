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

def mount_and_copy_with_kpartx(output_hdi, src_file, dst_filename):
    """
    kpartx を用いて HDI イメージからパーティションをマッピングし、そのパーティションに
    ファイルをコピーする処理です。パーティションマッピングが見つからなかった場合は、
    ループデバイス自体をマウントするフォールバックを試みます。
    """
    # ループデバイスにディスクイメージを関連付ける
    losetup_proc = subprocess.run(
        ["sudo", "losetup", "-f", "--show", output_hdi],
        capture_output=True, text=True
    )
    if losetup_proc.returncode != 0:
        print("Error setting up loop device:", losetup_proc.stderr)
        return False

    loop_dev = losetup_proc.stdout.strip()
    print("Loop device assigned:", loop_dev)

    # kpartx によるパーティションマッピングを作成
    kpartx_proc = subprocess.run(
        ["sudo", "kpartx", "-av", loop_dev],
        capture_output=True, text=True
    )
    partition_mapped = False
    mapped_partition = None
    for line in kpartx_proc.stdout.splitlines():
        parts = line.split()
        # 出力例: "add map loop0p1 (254:0): 0 123456 linear /dev/loop0 2048"
        if len(parts) >= 3 and parts[0] == "add" and "map" in parts[1]:
            mapped_partition = f"/dev/mapper/{parts[1]}"
            partition_mapped = True
            break

    if not mapped_partition:
        print("No partition mapping found. Trying to mount the loop device directly.")
        mapped_partition = loop_dev
    else:
        print("Mapped partition device:", mapped_partition)

    # 一時マウントポイントを作成
    mount_dir = tempfile.mkdtemp(prefix="hdi_mount_")
    mounted = False
    try:
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

        # マウント先にファイルをコピー
        dst_path = os.path.join(mount_dir, dst_filename)
        ret = subprocess.run(
            ["sudo", "cp", src_file, dst_path],
            capture_output=True, text=True
        )
        if ret.returncode != 0:
            print("Error copying file to mounted image:", ret.stderr)
            return False
        print("File copied successfully to", dst_path)
    finally:
        subprocess.run(["sudo", "umount", mount_dir])
        shutil.rmtree(mount_dir)
        if partition_mapped:
            subprocess.run(["sudo", "kpartx", "-dv", loop_dev], capture_output=True, text=True)
        subprocess.run(["sudo", "losetup", "-d", loop_dev], capture_output=True, text=True)
    return True

def process_hdi(hdi_path, output_hdi):
    # オリジナルのHDIファイルをバックアップとしてコピー
    shutil.copy2(hdi_path, output_hdi)

    # 作業用ディレクトリに nopporo.exe を作成
    exe_filename = "nopporo.exe"
    create_nopporo_exe(exe_filename)

    # まずはマウント＋コピーによる注入を試みる
    if not mount_and_copy_with_kpartx(output_hdi, exe_filename, "nopporo.exe"):
        print("Mount injection failed. Trying pyfatfs injection for FAT file system.")
        try:
            from pyfatfs import PyFat
        except ImportError as e:
            print("pyfatfs not installed; falling back to appending nopporo.exe to the disk image.")
            use_pyfat = False
        else:
            use_pyfat = True

        if use_pyfat:
            try:
                pf = PyFat()
                with open(output_hdi, "r+b") as fat_image:
                    pf.open_fat(fat_image)
                    # FAT系は大文字推奨なのでルート直下に /NOPPORO.EXE として作成
                    pf.create_file("/NOPPORO.EXE")
                    with pf.open("/NOPPORO.EXE", "wb") as f:
                        with open(exe_filename, "rb") as f_exe:
                            data = f_exe.read()
                        f.write(data)
                    # 変更内容を反映
                    fat_image.seek(0)
                    fat_image.write(pf.get_image())
                print("Successfully injected nopporo.exe using pyfatfs.")
            except Exception as e:
                print("pyfatfs injection failed:", e)
                print("Falling back to appending nopporo.exe to the disk image.")
                try:
                    with open(exe_filename, "rb") as f_exe:
                        exe_data = f_exe.read()
                    with open(output_hdi, "ab") as f_hdi:
                        f_hdi.write(exe_data)
                    print("Successfully appended nopporo.exe to the disk image.")
                except Exception as e2:
                    print("Error appending nopporo.exe:", e2)
        else:
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
