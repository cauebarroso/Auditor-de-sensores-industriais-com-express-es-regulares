import automata.Automaton;
import file.XMLCodec;
import gui.viewer.AutomatonPane;
import java.awt.Color;
import java.awt.Graphics2D;
import java.awt.Rectangle;
import java.awt.RenderingHints;
import java.awt.image.BufferedImage;
import java.io.File;
import javax.imageio.ImageIO;

/**
 * Desenha um arquivo .jff com o próprio componente gráfico do JFLAP 7.1
 * (o mesmo da janela do editor) e salva a imagem em PNG.
 *
 * Uso: java -Djava.awt.headless=true -cp "JFLAP7.1.jar;." DesenhaJFLAP ER-01.jff ER-01.png
 */
public class DesenhaJFLAP {
    public static void main(String[] args) throws Exception {
        Automaton automato = (Automaton) new XMLCodec().decode(new File(args[0]), null);
        AutomatonPane painel = new AutomatonPane(automato);
        painel.setAdapt(false);

        // Área ocupada pelos estados, com margem para os rótulos empilhados
        Rectangle area = null;
        for (automata.State estado : automato.getStates()) {
            Rectangle ponto = new Rectangle(estado.getPoint().x, estado.getPoint().y, 1, 1);
            area = area == null ? ponto : area.union(ponto);
        }
        int largura = area.x + area.width + 80;
        int altura = area.y + area.height + 80;

        painel.setSize(largura, altura);
        BufferedImage imagem = new BufferedImage(largura, altura, BufferedImage.TYPE_INT_RGB);
        Graphics2D g = imagem.createGraphics();
        g.setRenderingHint(RenderingHints.KEY_ANTIALIASING, RenderingHints.VALUE_ANTIALIAS_ON);
        g.setRenderingHint(RenderingHints.KEY_TEXT_ANTIALIASING, RenderingHints.VALUE_TEXT_ANTIALIAS_ON);
        g.setColor(Color.WHITE);
        g.fillRect(0, 0, largura, altura);
        painel.paintComponent(g);
        g.dispose();
        ImageIO.write(imagem, "png", new File(args[1]));
    }
}
