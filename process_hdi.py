import os
import shutil
import subprocess
import tempfile
import zipfile

def create_nopporo_exe(path):
    # ASCIIアートとメッセージを含むnopporo.exeの内容を作成
    ascii_art = r"""
   
                                            .....-+***********+-.....                               
                                        ....-***********************-....                           
                                     ....-*****************************=....                        
                                     .:+*********************************+:.                        
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
    kpartx を用いて HDI イメージからパーティションをマッピングし、
    そのうちの1つにファイルをコピーする処理です。
    パーティションマッピングが見つからなかった場合は、イメージ自体が
    直接ファイルシステムとしてマウント可能であると判断し、
    ループデバイス自体をマウントするようにフォールバックします。
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
        # パーティションマッピングが得られなかった場合、ループデバイス自体を使用
        print("No partition mapping found. Trying to mount the loop device directly.")
        mapped_partition = loop_dev
    else:
        print("Mapped partition device:", mapped_partition)

    # 一時マウントポイントを作成
    mount_dir = tempfile.mkdtemp(prefix="hdi_mount_")
    mounted = False
    try:
        # 一般的なファイルシステムタイプでマウントを試行
        for fs_type in ["vfat", "msdos", "ntfs", "ext2", "ext3", "ext4"]:
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
        # マウント解除と一時ディレクトリの削除
        subprocess.run(["sudo", "umount", mount_dir])
        shutil.rmtree(mount_dir)
        # パーティションマッピングがあった場合のみ kpartx の解除を実施
        if partition_mapped:
            subprocess.run(["sudo", "kpartx", "-dv", loop_dev], capture_output=True, text=True)
        # ループデバイスの解放
        subprocess.run(["sudo", "losetup", "-d", loop_dev], capture_output=True, text=True)
    return True

def process_hdi(hdi_path, output_hdi):
    # オリジナルのHDIファイルをバックアップとしてコピー
    shutil.copy2(hdi_path, output_hdi)

    # 作業用ディレクトリにnopporo.exeを作成
    exe_filename = "nopporo.exe"
    create_nopporo_exe(exe_filename)

    # kpartxを使い、HDIイメージ内のパーティションにファイルを注入
    if not mount_and_copy_with_kpartx(output_hdi, exe_filename, "nopporo.exe"):
        print("Failed to inject nopporo.exe into the HDI image; proceeding without injection.")
    else:
        print("Successfully injected nopporo.exe into", output_hdi)

    # 一時ファイルの削除
    if os.path.exists(exe_filename):
        os.remove(exe_filename)

    # HDIイメージをZIP圧縮（最大圧縮）して保存
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
