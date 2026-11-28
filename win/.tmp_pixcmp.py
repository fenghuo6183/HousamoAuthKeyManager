from PIL import Image
pts = {'nav1': (760, 300), 'nav2': (900, 600), 'card': (1600, 500), 'rail': (300, 900)}
for name in ('rail0_settings','rail25_settings','rail100_settings'):
    im = Image.open('../.tmp/%s.png' % name).convert('RGB')
    print(name, {k: im.getpixel(v) for k, v in pts.items()})
