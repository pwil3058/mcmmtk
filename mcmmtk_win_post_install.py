import os
import sys
import shutil
import distutils.sysconfig

NAME = "ModellersColourMatcherMixer"

desktop_dir = get_special_folder_path("CSIDL_DESKTOPDIRECTORY")
icon_file = os.path.join(distutils.sysconfig.PREFIX, "share", "pixmaps", "mcmmtk.ico")
start_menu = get_special_folder_path("CSIDL_STARTMENU")
start_menu_dir = os.path.join(start_menu, NAME)
data_dir = os.path.join(distutils.sysconfig.PREFIX, "share", NAME, "data")
standards_dir = os.path.join(distutils.sysconfig.PREFIX, "share", NAME, "standards")

if sys.argv[1] == "-install":
    os.mkdir(start_menu_dir)
    directory_created(start_menu_dir)
    for script, descr in [("mcmmtk.py", "Modellers' Colour Matching/Mixing Tool Kit")]:
        target = os.path.join(distutils.sysconfig.PREFIX, "Scripts", script)
        for link_dir in [desktop_dir, start_menu_dir]:
            link = os.path.join(link_dir, descr + ".lnk")
            create_shortcut(target, script, link, "",data_dir , icon_file)
            file_created(link)
            print("Created shortcut from {0} to {1}.".format(link, target))
elif sys.argv[1] == "-remove":
    pass
