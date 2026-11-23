package br.uva.aos.diag;

import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.core.annotation.Order;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

import java.io.IOException;

/**
 * FASE 1 - Filtro de diagnostico.
 *
 * Toda resposta da API carrega:
 *   X-Query-Count      -> quantos SQLs aquela requisicao executou
 *   X-Response-Time-Ms -> tempo medido no servidor (sem latencia de rede)
 *   X-Cache            -> HIT / MISS / BYPASS, quando aplicavel
 *
 * Com esses tres headers, qualquer afirmacao do relatorio pode ser conferida
 * com um simples `curl -i`, sem precisar abrir o banco ou o log.
 */
@Component
@Order(1) // antes de qualquer outro filtro, para medir o tempo total da requisicao
public class DiagnosticoFilter extends OncePerRequestFilter {

    @Override
    protected void doFilterInternal(HttpServletRequest request,
                                    HttpServletResponse response,
                                    FilterChain chain) throws ServletException, IOException {
        QueryCountHolder.reset();
        CacheStatusHolder.clear();
        long inicio = System.nanoTime();

        // Os headers precisam ser escritos ANTES do corpo ser enviado (resposta
        // comitada nao aceita header novo). Por isso usamos um wrapper que grava
        // os headers no momento em que o corpo comeca a ser escrito.
        HttpServletResponse resposta = new HeaderOnCommitResponse(response, inicio);
        try {
            chain.doFilter(request, resposta);
        } finally {
            // Se nada foi escrito (ex.: 204), grava aqui.
            if (!resposta.isCommitted()) {
                escreverHeaders(resposta, inicio);
            }
            QueryCountHolder.clear();
            CacheStatusHolder.clear();
        }
    }

    private static void escreverHeaders(HttpServletResponse response, long inicio) {
        double ms = (System.nanoTime() - inicio) / 1_000_000.0;
        response.setHeader("X-Query-Count", String.valueOf(QueryCountHolder.get()));
        response.setHeader("X-Response-Time-Ms", String.format(java.util.Locale.US, "%.2f", ms));
        CacheStatusHolder.Status status = CacheStatusHolder.get();
        if (status != null) {
            response.setHeader("X-Cache", status.name());
        }
    }

    /** Escreve os headers de diagnostico no instante em que a resposta e comitada. */
    private static class HeaderOnCommitResponse extends jakarta.servlet.http.HttpServletResponseWrapper {
        private final long inicio;
        private boolean escrito;

        HeaderOnCommitResponse(HttpServletResponse response, long inicio) {
            super(response);
            this.inicio = inicio;
        }

        private void garantirHeaders() {
            if (!escrito && !isCommitted()) {
                escrito = true;
                escreverHeaders((HttpServletResponse) getResponse(), inicio);
            }
        }

        @Override
        public jakarta.servlet.ServletOutputStream getOutputStream() throws IOException {
            garantirHeaders();
            return super.getOutputStream();
        }

        @Override
        public java.io.PrintWriter getWriter() throws IOException {
            garantirHeaders();
            return super.getWriter();
        }

        @Override
        public void flushBuffer() throws IOException {
            garantirHeaders();
            super.flushBuffer();
        }
    }
}
