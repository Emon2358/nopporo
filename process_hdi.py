import os
import shutil
import subprocess
import gzip

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
    # Write the dummy executable file that outputs the ASCII art and message.
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

def process_hdi(hdi_path, output_hdi):
    # Copy the original HDI file to a new file so that we keep the original intact.
    shutil.copy2(hdi_path, output_hdi)
    
    # Create nopporo.exe in the working directory
    exe_filename = "nopporo.exe"
    create_nopporo_exe(exe_filename)
    
    # Use mtools to inject nopporo.exe into the HDI.
    # Set MTOOLS_SKIP_CHECK to 1 to skip drive type checking.
    env = os.environ.copy()
    env["MTOOLS_SKIP_CHECK"] = "1"
    # The following command copies nopporo.exe into the root directory of the disk image.
    result = subprocess.run(["mcopy", "-i", output_hdi, exe_filename, "::/" + exe_filename],
                             capture_output=True, text=True, env=env)
    if result.returncode != 0:
         print("Error injecting nopporo.exe:", result.stderr)
    else:
         print("Successfully injected nopporo.exe into", output_hdi)
    
    # Clean up the temporary exe file.
    os.remove(exe_filename)
    
    # Compress the modified disk image with maximum gzip compression.
    compressed_output = output_hdi + ".gz"
    with open(output_hdi, 'rb') as f_in:
       data = f_in.read()
    with gzip.open(compressed_output, 'wb', compresslevel=9) as f_out:
       f_out.write(data)
       
    # Rename the compressed file to the final name.
    final_name = "disk_modified_compressed.hdi.gz"
    os.rename(compressed_output, final_name)
    print("Compressed disk image saved as", final_name)

if __name__ == "__main__":
    # Assume disk.hdi is in the repository root.
    input_hdi = "disk.hdi"
    output_hdi = "disk_modified.hdi"
    if not os.path.exists(input_hdi):
        print(f"Input HDI file '{input_hdi}' not found.")
    else:
        process_hdi(input_hdi, output_hdi)
        print(f"Processed HDI file saved as '{output_hdi}'.")
