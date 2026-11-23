package br.uva.aos.diag;

import net.ttddyy.dsproxy.listener.QueryExecutionListener;
import net.ttddyy.dsproxy.ExecutionInfo;
import net.ttddyy.dsproxy.QueryInfo;
import net.ttddyy.dsproxy.support.ProxyDataSource;
import net.ttddyy.dsproxy.support.ProxyDataSourceBuilder;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.config.BeanPostProcessor;
import org.springframework.context.annotation.Configuration;

import javax.sql.DataSource;
import java.util.List;

/**
 * FASE 1 - Contagem de SQL com datasource-proxy.
 *
 * Envolvemos o DataSource do Hikari num proxy que recebe um evento a cada
 * execucao JDBC. Isso e mais confiavel que ler o log do Hibernate porque:
 *   - conta tambem SQL nativo e queries emitidas fora do Hibernate;
 *   - permite somar por requisicao (ThreadLocal) sem parsear texto de log;
 *   - nao depende de deixar o log de SQL ligado (log distorce teste de carga).
 *
 * Uma execucao em lote (batch) conta como N queries, pois e isso que o banco
 * de fato executa.
 */
@Configuration
public class DataSourceProxyConfig implements BeanPostProcessor {

    private static final Logger SQL_LOG = LoggerFactory.getLogger("br.uva.aos.diag.sql");

    @Override
    public Object postProcessAfterInitialization(Object bean, String beanName) {
        if (bean instanceof DataSource dataSource && !(bean instanceof ProxyDataSource)) {
            return ProxyDataSourceBuilder.create(dataSource)
                    .name("a2-ds-proxy")
                    .listener(new ContadorListener())
                    .build();
        }
        return bean;
    }

    private static class ContadorListener implements QueryExecutionListener {
        @Override
        public void beforeQuery(ExecutionInfo execInfo, List<QueryInfo> queryInfoList) {
            // nada: contamos apos a execucao para registrar o que realmente rodou
        }

        @Override
        public void afterQuery(ExecutionInfo execInfo, List<QueryInfo> queryInfoList) {
            int quantidade = 0;
            for (QueryInfo info : queryInfoList) {
                // Em batch, parametersList tem uma entrada por execucao real.
                int execucoes = Math.max(1, info.getParametersList().size());
                quantidade += execucoes;
            }
            QueryCountHolder.increment(quantidade);

            if (SQL_LOG.isDebugEnabled()) {
                for (QueryInfo info : queryInfoList) {
                    SQL_LOG.debug("[{} ms] {}", execInfo.getElapsedTime(), info.getQuery());
                }
            }
        }
    }
}
