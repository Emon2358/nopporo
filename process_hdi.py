import os
import shutil
import subprocess
import tempfile
import zipfile

def create_nopporo_exe(path):
    # ASCII art and message displayed when nopporo.exe is run
    ascii_art = r"""
 
                                                :=*************+:                                   
                                           ==***********************==                              
                                        ==*****************************==                           
                                      =***********************************=                         
                                    +***************************************+                       
                                   +*****************************************+                      
                                 -*********************************************-                    
                                -***********************************************-                   
                                *********+*+************************+++**********                   
                              :********:      +******************=       +********:                 
                              =*******         +****************:         +*******+                 
                             -********         :***************+          -********-                
                             +********         =****************-         +********+                
                             **********=      +******************=.      **********+                
                             *******************************************************                
                             ***********************++******************************                
                             +**********************-+***** ***********************+                
                             +*********************  +***** =**********************+                
                             :********************-  +*****   *********************:                
                              +******************=   +*****   -*******************+                 
                              =*****************:    +*****    =******************=                 
                               :*************************************************:                  
                                :***********************************************:                   
                                 :*********************************************:                    
                                   =                                         =                      
                                     -=====:+++++=-====- ======-==+++-======                        
                                     ****** =****:=****+ ****** +***+ ******                        
-++++++++++++++++++++++++=           ****** =***= =****+ ****** -***- ******             +++++++++=:
  =+***********************+:        ::::::  +**  ::::::.:----- -***  ::::::          -*********+.  
     *************************+              :*=                 =*=               :+********+=     
        =************************+            +                   =              =********+=        
           +************************:                                         -*********=           
            .-************************=:                                   :*********-              
                =************************-                              ++********=                 
                  :+************************+                        ==********+                    
                     -+***********************+:                  -+********+-                      
                        =************************=             :+********+=                         
                          =+************************-        =*********+                            
                             ==************************=  :*********+                               
                                :********************= .*********=                                  
                                   =***************:++********+                                     
                                     -+*********-=+***********=-                                    
                                   :+*******+=-=*****************+:                                 
                                 +********+ =***********************=                               
                              -********+-     ++***********************:                            
                           =********+=           =***********************+                          
                        :********+-                -+***********************=                       
                      +*******+:                      :************************=                    
                  :+********-                            =***********************+=                 
               =+********=                                 :+***********************+-              
            -+********+:                                      -************************=:           
         -+********+-                                            =************************=         
      .+********+=                                                 -+***********************+=      
    =********+=                                                      .=+***********************+-   
 -*********-                                                             =************************+.
    """
    message = "created by Emon support by nopporo"
    content = ascii_art + "\n" + message + "\n"
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

def mount_and_copy(loop_dev, mount_dir, src_file, dst_filename):
    # Attempt to mount the loop device.
    ret = subprocess.run(["sudo", "mount", loop_dev, mount_dir], capture_output=True, text=True)
    if ret.returncode != 0:
        print("Error mounting loop device:", ret.stderr)
        return False
    # Copy the file into the mounted directory.
    dst_path = os.path.join(mount_dir, dst_filename)
    ret = subprocess.run(["sudo", "cp", src_file, dst_path], capture_output=True, text=True)
    if ret.returncode != 0:
        print("Error copying file to mounted image:", ret.stderr)
        subprocess.run(["sudo", "umount", mount_dir])
        return False
    # Unmount the loop device.
    ret = subprocess.run(["sudo", "umount", mount_dir], capture_output=True, text=True)
    if ret.returncode != 0:
        print("Error unmounting loop device:", ret.stderr)
        return False
    return True

def process_hdi(hdi_path, output_hdi):
    # Copy the original HDI file to keep it intact.
    shutil.copy2(hdi_path, output_hdi)

    # Create nopporo.exe in the working directory.
    exe_filename = "nopporo.exe"
    create_nopporo_exe(exe_filename)

    # Set up a temporary mount point.
    mount_dir = tempfile.mkdtemp(prefix="hdi_mount_")

    try:
        # Associate the disk image with a loop device.
        losetup_proc = subprocess.run(["sudo", "losetup", "-f", "--show", output_hdi],
                                      capture_output=True, text=True)
        if losetup_proc.returncode != 0:
            print("Error setting up loop device:", losetup_proc.stderr)
        else:
            loop_dev = losetup_proc.stdout.strip()
            print("Loop device assigned:", loop_dev)

            # Attempt to mount the loop device and copy the file.
            if not mount_and_copy(loop_dev, mount_dir, exe_filename, "nopporo.exe"):
                print("Failed to inject nopporo.exe into the HDI image; proceeding without injection.")
            else:
                print("Successfully injected nopporo.exe into", output_hdi)

            # Detach the loop device.
            ret = subprocess.run(["sudo", "losetup", "-d", loop_dev],
                                 capture_output=True, text=True)
            if ret.returncode != 0:
                print("Error detaching loop device:", ret.stderr)
    finally:
        # Clean up the temporary mount directory.
        shutil.rmtree(mount_dir)
        # Remove the temporary exe file.
        if os.path.exists(exe_filename):
            os.remove(exe_filename)

    # Compress the modified disk image with maximum compression into a ZIP file.
    final_name = "disk_modified_compressed.hdi.zip"
    with zipfile.ZipFile(final_name, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zipf:
        zipf.write(output_hdi, arcname=os.path.basename(output_hdi))
    print("Compressed disk image saved as", final_name)

if __name__ == "__main__":
    input_hdi = "disk.hdi"
    output_hdi = "disk_modified.hdi"
    if not os.path.exists(input_hdi):
        print(f"Input HDI file '{input_hdi}' not found.")
    else:
        process_hdi(input_hdi, output_hdi)
        print(f"Processed HDI file saved as '{output_hdi}'.")
