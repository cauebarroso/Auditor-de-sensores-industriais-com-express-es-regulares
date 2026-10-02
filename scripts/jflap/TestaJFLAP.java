import automata.Automaton;
import automata.fsa.FSAStepWithClosureSimulator;
import file.XMLCodec;
import java.io.*;
import java.nio.charset.StandardCharsets;

/**
 * Carrega um arquivo .jff com o próprio JFLAP 7.1 e simula cada linha do
 * arquivo de entradas (o mesmo usado em Input > Multiple Run).
 * Saída: ACEITA ou REJEITA, uma linha por cadeia.
 *
 * Compilar: javac -cp JFLAP7.1.jar -d . TestaJFLAP.java
 * Executar: java -cp "JFLAP7.1.jar;." TestaJFLAP ER-01.jff entradas/ER-01.txt
 */
public class TestaJFLAP {
    public static void main(String[] args) throws Exception {
        Automaton automato = (Automaton) new XMLCodec().decode(new File(args[0]), null);
        try (BufferedReader entradas = new BufferedReader(
                new InputStreamReader(new FileInputStream(args[1]), StandardCharsets.UTF_8))) {
            String cadeia;
            while ((cadeia = entradas.readLine()) != null) {
                FSAStepWithClosureSimulator simulador = new FSAStepWithClosureSimulator(automato);
                System.out.println(simulador.simulateInput(cadeia) ? "ACEITA" : "REJEITA");
            }
        }
    }
}
