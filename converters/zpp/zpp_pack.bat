pyinstaller -y zpp.py --add-binary="C:\ffmpeg\ffmpeg.exe;." --add-binary="C:\ffmpeg\ffprobe.exe;."
path=%~dp0\dist\zpp\
echo %%~dp0\zpp.exe %%1>>"%path%\zpp_convert.bat"
echo pause>>"%path%\zpp_convert.bat"