<?php

/**
 * ═══════════════════════════════════════════════════════════════════════
 * CALCULADORA DE ECONOMIA - OTIMIZAÇÃO DYNAMODB
 * ═══════════════════════════════════════════════════════════════════════
 *
 * Este script calcula a economia estimada em custos de DynamoDB
 * após a implementação das otimizações.
 *
 * COMO USAR:
 * 1. Ajuste as constantes abaixo com seus dados reais
 * 2. Execute: php calculadora_economia_dynamodb.php
 * 3. Analise o relatório de economia
 *
 * ═══════════════════════════════════════════════════════════════════════
 */

class CalculadoraEconomiaDynamoDB
{
    // ═══════════════════════════════════════════════════════════════════════
    // CONFIGURAÇÕES - AJUSTE CONFORME SEU CENÁRIO
    // ═══════════════════════════════════════════════════════════════════════

    // Dados de uso
    const ALUNOS_ATIVOS_DIA = 10000;        // Alunos ativos por dia
    const AULAS_POR_CURSO = 100;            // Média de aulas por curso
    const CURSOS_POR_ALUNO = 2;             // Média de cursos por aluno
    const REQUESTS_DIA = 50000;             // Total de requests por dia

    // Custos AWS (us-east-1, pode variar por região)
    const CUSTO_RCU_1M = 0.25;              // USD por 1 milhão de RCUs
    const CUSTO_WCU_1M = 1.25;              // USD por 1 milhão de WCUs

    // Tamanho médio dos itens
    const TAMANHO_ITEM_KB = 1;              // KB por item (ajuste conforme real)

    // Percentual de cada operação no total
    const PCT_GET_VISUALIZADOS = 30;        // % de getVisualizadosWithLastKey
    const PCT_GET_AULAS_PDF = 20;           // % de getAulasPdfVisualizadas
    const PCT_GET_VIDEO_CURSO = 15;         // % de getVideoCursoWithLastKey
    const PCT_GET_PDF_CURSO = 15;           // % de getPdfCursoWithLastKey
    const PCT_GET_SIMPLES = 15;             // % de queries simples (getVideoByAlunoVideo, etc)
    const PCT_WRITES = 5;                   // % de writes (registrar, bulk insert)

    // ═══════════════════════════════════════════════════════════════════════
    // CÁLCULOS
    // ═══════════════════════════════════════════════════════════════════════

    private $resultados = [];

    public function calcular()
    {
        echo "═══════════════════════════════════════════════════════════════════════\n";
        echo "  CALCULADORA DE ECONOMIA - OTIMIZAÇÃO DYNAMODB\n";
        echo "═══════════════════════════════════════════════════════════════════════\n\n";

        $this->calcularGetVisualizadosWithLastKey();
        $this->calcularGetAulasPdfVisualizadas();
        $this->calcularGetVideoCurso();
        $this->calcularGetPdfCurso();
        $this->calcularQueriesSimples();
        $this->calcularWrites();
        $this->calcularCacheImpact();

        $this->gerarRelatorio();
    }

    // ═══════════════════════════════════════════════════════════════════════
    // CÁLCULOS POR MÉTODO
    // ═══════════════════════════════════════════════════════════════════════

    private function calcularGetVisualizadosWithLastKey()
    {
        $requestsDia = self::REQUESTS_DIA * (self::PCT_GET_VISUALIZADOS / 100);

        // ANTES: Para cada aluno, assume 10 páginas em média (1000 items / 100 per page)
        $paginasMedias = 10;
        $queriesAntes = $requestsDia * $paginasMedias;

        // DEPOIS: 1 query por página
        $queriesDepois = $requestsDia * $paginasMedias;

        // RCUs: 1 RCU = 4KB strongly consistent, 8KB eventually consistent
        // Assume eventually consistent (2x mais barato)
        $rcuPorQuery = ceil(self::TAMANHO_ITEM_KB / 8);

        $rcusAntes = $queriesAntes * $rcuPorQuery;
        $rcusDepois = $queriesDepois * $rcuPorQuery;

        $this->resultados['getVisualizadosWithLastKey'] = [
            'metodo' => 'getVisualizadosWithLastKey',
            'requests_dia' => $requestsDia,
            'queries_antes' => $queriesAntes,
            'queries_depois' => $queriesDepois,
            'rcus_antes' => $rcusAntes,
            'rcus_depois' => $rcusDepois,
            'economia_rcus' => $rcusAntes - $rcusDepois,
            'economia_pct' => 0, // Não há economia aqui (já era otimizado em paginação)
            'observacao' => 'Economia em prevenir loops infinitos'
        ];
    }

    private function calcularGetAulasPdfVisualizadas()
    {
        $requestsDia = self::REQUESTS_DIA * (self::PCT_GET_AULAS_PDF / 100);

        // ANTES: 1 query POR AULA (dentro do foreach)
        $aulasMedia = 100; // Assume 100 aulas consultadas por request
        $queriesAntes = $requestsDia * $aulasMedia;

        // DEPOIS: 1 query POR CHUNK (chunks de 100)
        $chunksMedia = ceil($aulasMedia / 100);
        $queriesDepois = $requestsDia * $chunksMedia;

        $rcuPorQuery = ceil(self::TAMANHO_ITEM_KB / 8);

        $rcusAntes = $queriesAntes * $rcuPorQuery;
        $rcusDepois = $queriesDepois * $rcuPorQuery;

        $this->resultados['getAulasPdfVisualizadas'] = [
            'metodo' => 'getAulasPdfVisualizadas',
            'requests_dia' => $requestsDia,
            'queries_antes' => $queriesAntes,
            'queries_depois' => $queriesDepois,
            'rcus_antes' => $rcusAntes,
            'rcus_depois' => $rcusDepois,
            'economia_rcus' => $rcusAntes - $rcusDepois,
            'economia_pct' => (($rcusAntes - $rcusDepois) / $rcusAntes) * 100,
            'observacao' => 'MAIOR ECONOMIA - Query única por chunk'
        ];
    }

    private function calcularGetVideoCurso()
    {
        $requestsDia = self::REQUESTS_DIA * (self::PCT_GET_VIDEO_CURSO / 100);

        // Assume paginação similar
        $paginasMedias = 5;
        $queriesAntes = $requestsDia * $paginasMedias;
        $queriesDepois = $requestsDia * $paginasMedias;

        $rcuPorQuery = ceil(self::TAMANHO_ITEM_KB / 8);

        $rcusAntes = $queriesAntes * $rcuPorQuery;
        $rcusDepois = $queriesDepois * $rcuPorQuery;

        $this->resultados['getVideoCurso'] = [
            'metodo' => 'getVideoCursoWithLastKey',
            'requests_dia' => $requestsDia,
            'queries_antes' => $queriesAntes,
            'queries_depois' => $queriesDepois,
            'rcus_antes' => $rcusAntes,
            'rcus_depois' => $rcusDepois,
            'economia_rcus' => 0,
            'economia_pct' => 0,
            'observacao' => 'Economia em limites de segurança'
        ];
    }

    private function calcularGetPdfCurso()
    {
        $requestsDia = self::REQUESTS_DIA * (self::PCT_GET_PDF_CURSO / 100);

        $paginasMedias = 5;
        $queriesAntes = $requestsDia * $paginasMedias;
        $queriesDepois = $requestsDia * $paginasMedias;

        $rcuPorQuery = ceil(self::TAMANHO_ITEM_KB / 8);

        $rcusAntes = $queriesAntes * $rcuPorQuery;
        $rcusDepois = $queriesDepois * $rcuPorQuery;

        $this->resultados['getPdfCurso'] = [
            'metodo' => 'getPdfCursoWithLastKey',
            'requests_dia' => $requestsDia,
            'queries_antes' => $queriesAntes,
            'queries_depois' => $queriesDepois,
            'rcus_antes' => $rcusAntes,
            'rcus_depois' => $rcusDepois,
            'economia_rcus' => 0,
            'economia_pct' => 0,
            'observacao' => 'Economia em limites de segurança'
        ];
    }

    private function calcularQueriesSimples()
    {
        $requestsDia = self::REQUESTS_DIA * (self::PCT_GET_SIMPLES / 100);

        // Queries simples: 1 query por request
        $queriesAntes = $requestsDia;
        $queriesDepois = $requestsDia;

        $rcuPorQuery = ceil(self::TAMANHO_ITEM_KB / 8);

        $rcusAntes = $queriesAntes * $rcuPorQuery;
        $rcusDepois = $queriesDepois * $rcuPorQuery;

        $this->resultados['queriesSimples'] = [
            'metodo' => 'Queries simples (get, getAllVideo, etc)',
            'requests_dia' => $requestsDia,
            'queries_antes' => $queriesAntes,
            'queries_depois' => $queriesDepois,
            'rcus_antes' => $rcusAntes,
            'rcus_depois' => $rcusDepois,
            'economia_rcus' => 0,
            'economia_pct' => 0,
            'observacao' => 'Sem mudança nas queries'
        ];
    }

    private function calcularWrites()
    {
        $requestsDia = self::REQUESTS_DIA * (self::PCT_WRITES / 100);

        // Writes não mudam
        $wcusAntes = $requestsDia;
        $wcusDepois = $requestsDia;

        $this->resultados['writes'] = [
            'metodo' => 'Writes (registrar, bulkInsert)',
            'requests_dia' => $requestsDia,
            'queries_antes' => $requestsDia,
            'queries_depois' => $requestsDia,
            'wcus_antes' => $wcusAntes,
            'wcus_depois' => $wcusDepois,
            'economia_wcus' => 0,
            'economia_pct' => 0,
            'observacao' => 'Writes não foram alterados'
        ];
    }

    private function calcularCacheImpact()
    {
        // Cache pode reduzir 50-80% das reads repetidas
        // Assume 60% das queries simples podem ser cacheadas
        $hitRate = 0.6;

        $requestsSimples = self::REQUESTS_DIA * (self::PCT_GET_SIMPLES / 100);
        $queriesEvitadas = $requestsSimples * $hitRate;
        $rcuPorQuery = ceil(self::TAMANHO_ITEM_KB / 8);
        $rcusEconomizados = $queriesEvitadas * $rcuPorQuery;

        $this->resultados['cache'] = [
            'metodo' => 'Cache (60% hit rate)',
            'requests_dia' => $requestsSimples,
            'hit_rate' => $hitRate * 100,
            'queries_evitadas' => $queriesEvitadas,
            'rcus_economizados' => $rcusEconomizados,
            'economia_pct' => $hitRate * 100,
            'observacao' => 'Maior impacto em queries frequentes'
        ];
    }

    // ═══════════════════════════════════════════════════════════════════════
    // RELATÓRIO
    // ═══════════════════════════════════════════════════════════════════════

    private function gerarRelatorio()
    {
        echo "\n═══════════════════════════════════════════════════════════════════════\n";
        echo "  RELATÓRIO DE ECONOMIA - POR MÉTODO\n";
        echo "═══════════════════════════════════════════════════════════════════════\n\n";

        $totalRcusAntes = 0;
        $totalRcusDepois = 0;
        $totalRcusCache = 0;

        foreach ($this->resultados as $key => $res) {
            if ($key === 'writes' || $key === 'cache') continue;

            echo "📊 {$res['metodo']}\n";
            echo "   Requests/dia: " . number_format($res['requests_dia']) . "\n";
            echo "   Queries ANTES: " . number_format($res['queries_antes']) . "\n";
            echo "   Queries DEPOIS: " . number_format($res['queries_depois']) . "\n";
            echo "   RCUs ANTES: " . number_format($res['rcus_antes']) . "\n";
            echo "   RCUs DEPOIS: " . number_format($res['rcus_depois']) . "\n";

            if ($res['economia_rcus'] > 0) {
                echo "   💰 ECONOMIA: " . number_format($res['economia_rcus']) . " RCUs/dia ";
                echo "(" . number_format($res['economia_pct'], 1) . "%)\n";
            }

            echo "   📝 {$res['observacao']}\n\n";

            $totalRcusAntes += $res['rcus_antes'];
            $totalRcusDepois += $res['rcus_depois'];
        }

        // Cache
        $cacheRes = $this->resultados['cache'];
        echo "📊 {$cacheRes['metodo']}\n";
        echo "   Hit rate: " . $cacheRes['hit_rate'] . "%\n";
        echo "   Queries evitadas: " . number_format($cacheRes['queries_evitadas']) . "\n";
        echo "   💰 ECONOMIA: " . number_format($cacheRes['rcus_economizados']) . " RCUs/dia\n";
        echo "   📝 {$cacheRes['observacao']}\n\n";

        $totalRcusCache = $cacheRes['rcus_economizados'];
        $totalRcusDepoisComCache = $totalRcusDepois - $totalRcusCache;

        // Totais
        echo "═══════════════════════════════════════════════════════════════════════\n";
        echo "  TOTAIS\n";
        echo "═══════════════════════════════════════════════════════════════════════\n\n";

        echo "RCUs/dia ANTES: " . number_format($totalRcusAntes) . "\n";
        echo "RCUs/dia DEPOIS (sem cache): " . number_format($totalRcusDepois) . "\n";
        echo "RCUs/dia DEPOIS (com cache): " . number_format($totalRcusDepoisComCache) . "\n\n";

        $economiaSemCache = $totalRcusAntes - $totalRcusDepois;
        $economiaComCache = $totalRcusAntes - $totalRcusDepoisComCache;

        echo "💰 ECONOMIA SEM CACHE: " . number_format($economiaSemCache) . " RCUs/dia ";
        $pctSemCache = ($economiaSemCache / $totalRcusAntes) * 100;
        echo "(" . number_format($pctSemCache, 1) . "%)\n";

        echo "💰 ECONOMIA COM CACHE: " . number_format($economiaComCache) . " RCUs/dia ";
        $pctComCache = ($economiaComCache / $totalRcusAntes) * 100;
        echo "(" . number_format($pctComCache, 1) . "%)\n\n";

        // Custos
        echo "═══════════════════════════════════════════════════════════════════════\n";
        echo "  IMPACTO FINANCEIRO\n";
        echo "═══════════════════════════════════════════════════════════════════════\n\n";

        $custoAntesDia = ($totalRcusAntes / 1000000) * self::CUSTO_RCU_1M;
        $custoDepoisDia = ($totalRcusDepoisComCache / 1000000) * self::CUSTO_RCU_1M;

        $custoAntesMes = $custoAntesDia * 30;
        $custoDepoisMes = $custoDepoisDia * 30;

        $economiaDia = $custoAntesDia - $custoDepoisDia;
        $economiaMes = $economiaDia * 30;
        $economiaAno = $economiaDia * 365;

        echo "💵 Custo ANTES:\n";
        echo "   Por dia: $" . number_format($custoAntesDia, 2) . "\n";
        echo "   Por mês: $" . number_format($custoAntesMes, 2) . "\n\n";

        echo "💵 Custo DEPOIS:\n";
        echo "   Por dia: $" . number_format($custoDepoisDia, 2) . "\n";
        echo "   Por mês: $" . number_format($custoDepoisMes, 2) . "\n\n";

        echo "💰 ECONOMIA:\n";
        echo "   Por dia: $" . number_format($economiaDia, 2) . "\n";
        echo "   Por mês: $" . number_format($economiaMes, 2) . "\n";
        echo "   Por ano: $" . number_format($economiaAno, 2) . "\n\n";

        $pctEconomia = ($economiaComCache / $totalRcusAntes) * 100;
        echo "📊 Redução total: " . number_format($pctEconomia, 1) . "%\n\n";

        // Recomendações
        echo "═══════════════════════════════════════════════════════════════════════\n";
        echo "  RECOMENDAÇÕES\n";
        echo "═══════════════════════════════════════════════════════════════════════\n\n";

        if ($pctEconomia > 50) {
            echo "✅ RECOMENDAÇÃO: IMPLEMENTAR IMEDIATAMENTE\n";
            echo "   A economia de " . number_format($pctEconomia, 1) . "% justifica implementação urgente.\n";
            echo "   ROI: Economia de $" . number_format($economiaMes, 2) . "/mês vs 4h de implementação\n\n";
        } elseif ($pctEconomia > 20) {
            echo "✅ RECOMENDAÇÃO: IMPLEMENTAR QUANDO POSSÍVEL\n";
            echo "   A economia de " . number_format($pctEconomia, 1) . "% é significativa.\n\n";
        } else {
            echo "⚠️  RECOMENDAÇÃO: AVALIAR OUTROS CENÁRIOS\n";
            echo "   A economia de " . number_format($pctEconomia, 1) . "% pode não justificar implementação.\n";
            echo "   Considere ajustar as constantes com dados reais.\n\n";
        }

        // Observações
        echo "📝 OBSERVAÇÕES:\n";
        echo "   - Valores baseados nas constantes configuradas no topo do arquivo\n";
        echo "   - Ajuste as constantes com seus dados reais para cálculo preciso\n";
        echo "   - Região AWS: us-east-1 (custos variam por região)\n";
        echo "   - RCU cost: $" . self::CUSTO_RCU_1M . " por milhão\n";
        echo "   - Não inclui custos de storage ou backups\n\n";
    }
}

// ═══════════════════════════════════════════════════════════════════════
// EXECUÇÃO
// ═══════════════════════════════════════════════════════════════════════

$calculadora = new CalculadoraEconomiaDynamoDB();
$calculadora->calcular();

echo "═══════════════════════════════════════════════════════════════════════\n\n";
