Kontrolu ĉu la tiparoj Fira Sans kaj Fira Mono estas jam instalitaj:

```bash
fc-list : family | grep "Fira"
```

Se ne, elŝutu ilin de CTAN kaj kopiu en la lokan arejon de tiparoj:

```bash
cd ~/Downloads
wget https://mirrors.ctan.org/install/fonts/fira.tds.zip
unzip fira.tds.zip -d FiraFontFam
mkdir -p ~/.local/share/fonts/fira
cp FiraFontFam/fonts/opentype/public/fira/* ~/.local/share/fonts/fira
rm -r FiraFontFam fira.tds.zip
```

Elŝutu Geotica_Three.otf (ekzemple, de FontSpring), malpaku, kaj kopiu
en la saman lokon:

```bash
mkdir -p ~/.local/share/fonts/geotica/
unzip ~/Downloads/geotica-three.zip -d ~/.local/share/fonts/geotica/
rm ~/Downloads/geotica-three.zip
```

Freŝigu la kaŝmemoron de la tiparoj:

```bash
sudo fc-cache -f -v
fc-list : family | grep -e "Fira" -e "Geotica"
```

Elŝutu FontAwesome kaj instalu ĝin aŭtomate aŭ permane.

*Opcio 1: Aŭtomate (preferindas)*

```bash
tlmgr init-usertree
tlmgr option repository http://mirror.ctan.org/systems/texlive/tlnet
tlmgr install fontawesome7
```

*Opcio 2: Permane*

```bash
cd ~/Downloads
wget https://mirrors.ctan.org/fonts/fontawesome7.zip
unzip fontawesome7.zip
FONTSDIR=$(kpsewhich -var-value=TEXMFHOME)
for dir_pair in \
  "tex:tex/latex" \
  "opentype:fonts/opentype" \
  "type1:fonts/type1" \
  "tfm:fonts/tfm" \
  "map:fonts/map/dvips" \
  "enc:fonts/enc/dvips"
do
  src_sub="${dir_pair%%:*}"
  dst_sub="${dir_pair#*:}"
  mkdir -p "$FONTSDIR/$dst_sub/fa7"
  mv ~/Downloads/fontawesome7/$src_sub/* "$FONTSDIR/$dst_sub/fa7"
done
mv ~/Downloads/fontawesome7/doc/fontawesome7.pdf .
rm -r fontawesome7 fontawesome7.zip
texhash "$FONTSDIR"
```

Se la instalado finiĝis senprobleme, la sekva komando printos la
plenan dosierindikon de FontAwesome por Latex:

```bash
kpsewhich fontawesome7.sty
```
