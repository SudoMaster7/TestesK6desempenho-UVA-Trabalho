package br.uva.aos.diag;

/**
 * Contador de SQL por REQUISICAO.
 *
 * Por que ThreadLocal? No Spring MVC (Tomcat), cada requisicao HTTP e atendida
 * por uma thread. Guardando o contador na thread conseguimos atribuir cada SQL
 * executado a requisicao que o disparou, mesmo com 200 usuarios simultaneos.
 *
 * E este numero que prova objetivamente os fenomenos do trabalho:
 *   - cache HIT  -> X-Query-Count: 0
 *   - N+1        -> X-Query-Count cresce junto com ?limite=
 *   - JOIN FETCH -> X-Query-Count constante (1 ou 2)
 */
public final class QueryCountHolder {

    private static final ThreadLocal<int[]> COUNT = ThreadLocal.withInitial(() -> new int[1]);

    private QueryCountHolder() {
    }

    public static void reset() {
        COUNT.get()[0] = 0;
    }

    public static void increment(int quantidade) {
        COUNT.get()[0] += quantidade;
    }

    public static int get() {
        return COUNT.get()[0];
    }

    public static void clear() {
        COUNT.remove();
    }
}
