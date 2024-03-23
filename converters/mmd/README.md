**Aplikacja do konwertowania dźwięków z symulatora "Maszyna" do formatu Dekodera dźwiękowego RB2300**

**Instalacja:**
1. Zainstaluj symulator [Maszyna](https://eu07.pl/pobierz/).
2. Pobierz konwerter z odpowiedniego repozytorium.
3. Rozpakuj go w dowolnym miejscu.
4. Zmień bieżącą ścieżkę do folderu z dźwiękami zainstalowanego symulatora "Maszyna" na rzeczywistą w plikach konwertera `mmd_convert_adpcm.bat` oraz `mmd_convert_ogg.bat`.

**Uruchamianie:**
1. Przejdź do folderu `Maszyna-Sim\dynamic\pkp` w folderze symulatora "Maszyna".
2. Znajdź odpowiedni plik \*.mmd dla wybranej lokomotywy.
3. Przeciągnij wybrany plik \*.mmd na plik `mmd_convert_adpcm.bat`, aby dokonać konwersji do formatu dekodera ADPCM (16kHz), lub na plik `mmd_convert_ogg.bat`, aby dokonać konwersji do formatu OGG (32kHz) potrzebnego do [Emulatora](https://www.railbox.pl/sounds) dekodera.
4. Po uruchomieniu konwersji pojawi się nowy folder o nazwie pliku \*.mmd, zawierający skonwertowane dźwięki.
*Uwaga:* Wygenerowany pakiet dźwięków jest podstawowym źródłem dla tworzenia własnego pakietu dźwiękowego i potrzebuje dopracowania na przykład za pomocą programu [Audacity](https://www.audacityteam.org/download/). Konwerter może wygenerować kilka dźwięków dla tej samej funkcji, jednak oprogramowanie dekodera tego nie wspiera i trzeba wybrać najbardziej pasujący dźwięk. Oryginalne pliki zaznaczone jako dźwięk w przedziale silnikowym będą mieć `_ENG` w nazwie pliku i prawdopodobnie potrzebują korekty.

**Dodatkowa informacja**
[Opis formatu mmd](https://wiki.eu07.pl/index.php/Plik_multimedi%C3%B3w_(mmd))