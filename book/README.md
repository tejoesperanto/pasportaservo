Instalu la aldonajn tiparojn uzatajn en la libro (ekz., Fira Sans):

```bash
sudo apt install texlive-fonts-extra
```

Elŝutu Geotica_Three.otf (ekzemple, de FontSpring), malpaku, kaj kopiu
en la saman lokon kie troviĝas PasportaSerto.tex:

```bash
mkdir -p ~/.local/share/fonts/geotica/
unzip ~/Downloads/geotica-three.zip -d ~/.local/share/fonts/geotica/
cp ~/.local/share/fonts/geotica/Geotica_Three.otf [PS_SOURCE_BASE_DIR]/book/templates/book/
```

Se la aldonaj tiparoj ne jam estas agorditaj, kreu la dosieron:

```bash
sudo nano /etc/fonts/conf.d/09-texlive-fonts.conf
```

kaj enmetu la jenan enhavon:

```xml
<?xml version="1.0"?>
<!DOCTYPE fontconfig SYSTEM "fonts.dtd">
<fontconfig>
  <dir>/usr/share/texlive/texmf-dist/fonts/opentype</dir>
  <dir>/usr/share/texlive/texmf-dist/fonts/truetype</dir>
</fontconfig>
```

Freŝigu la kaŝmemoron de la tiparoj:

```bash
sudo fc-cache -f -v
fc-list : family | grep -e "Fira" -e "Geotica"
```
