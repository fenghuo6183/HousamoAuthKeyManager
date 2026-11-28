import com.google.zxing.*;
import com.google.zxing.common.HybridBinarizer;
import javax.imageio.ImageIO;
import java.awt.image.BufferedImage;
import java.io.File;

public class QrDecode {
    public static void main(String[] a) throws Exception {
        BufferedImage img = ImageIO.read(new File(a[0]));
        int w = img.getWidth(), h = img.getHeight();
        int[] px = img.getRGB(0, 0, w, h, null, 0, w);
        LuminanceSource src = new RGBLuminanceSource(w, h, px);
        BinaryBitmap bmp = new BinaryBitmap(new HybridBinarizer(src));
        try {
            Result r = new MultiFormatReader().decode(bmp);
            System.out.println("TEXT=" + r.getText());
        } catch (NotFoundException e) {
            System.out.println("NO_QR");
        }
    }
}