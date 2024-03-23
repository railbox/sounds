pyinstaller -y mmd.py --add-binary="C:\ffmpeg\ffmpeg.exe;." --add-binary="C:\ffmpeg\ffprobe.exe;."
path=%~dp0\dist\mmd\
echo set sounds_path="D:\\Maszyna-Sim\\sounds">"%path%\mmd_convert_ogg.bat"
echo %%~dp0\mmd.exe %%sounds_path%% ogg %%1>>"%path%\mmd_convert_ogg.bat"
echo pause>>"%path%\mmd_convert_ogg.bat"

echo set sounds_path="D:\\Maszyna-Sim\\sounds">"%path%\mmd_convert_adpcm.bat"
echo %%~dp0\mmd.exe %%sounds_path%% adpcm %%1>>"%path%\mmd_convert_adpcm.bat"
echo pause>>"%path%\mmd_convert_adpcm.bat"