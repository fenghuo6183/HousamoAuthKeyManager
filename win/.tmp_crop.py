from PIL import Image
im = Image.open('../.tmp/connect_new.png')
im.crop((1800, 440, 2420, 580)).resize((1240, 280)).save('../.tmp/combo_zoom.png')
print(im.size)
