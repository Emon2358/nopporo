import os
import zipfile
import tempfile
import shutil

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
    # In this implementation, disk.hdi is treated as a ZIP archive. We extract its content,
    # add the nopporo.exe file, and then re-create the HDI file with maximum compression.
    temp_dir = tempfile.mkdtemp()
    try:
        with zipfile.ZipFile(hdi_path, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)
    except zipfile.BadZipFile:
        print("Error: The HDI file is not a valid zip archive.")
        shutil.rmtree(temp_dir)
        return

    # Create nopporo.exe in the extracted directory.
    exe_path = os.path.join(temp_dir, "nopporo.exe")
    create_nopporo_exe(exe_path)
    
    # Recreate the HDI file with maximum compression (compresslevel=9).
    with zipfile.ZipFile(output_hdi, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as zipf:
        for root, dirs, files in os.walk(temp_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, temp_dir)
                zipf.write(file_path, arcname)
    shutil.rmtree(temp_dir)

if __name__ == "__main__":
    # Assume disk.hdi is in the repository root.
    input_hdi = "disk.hdi"
    output_hdi = "disk_modified.hdi"
    if not os.path.exists(input_hdi):
        print(f"Input HDI file '{input_hdi}' not found.")
    else:
        process_hdi(input_hdi, output_hdi)
        print(f"Processed HDI file saved as '{output_hdi}'.")
