package br.uva.aos.diag;

/**
 * Marca o resultado do cache na requisicao atual, para o filtro expor no header
 * X-Cache. Mesma tecnica do contador de SQL: ThreadLocal por requisicao.
 *
 * HIT    = respondido pelo Redis, sem tocar no banco
 * MISS   = nao estava em cache; foi ao banco e gravou
 * BYPASS = endpoint que ignora o cache por definicao (/sem-cache)
 */
public final class CacheStatusHolder {

    public enum Status { HIT, MISS, BYPASS }

    private static final ThreadLocal<Status> STATUS = new ThreadLocal<>();

    private CacheStatusHolder() {
    }

    public static void set(Status status) {
        STATUS.set(status);
    }

    public static Status get() {
        return STATUS.get();
    }

    public static void clear() {
        STATUS.remove();
    }
}
