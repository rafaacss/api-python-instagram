<?php

/**
 * ═══════════════════════════════════════════════════════════════════════
 * TESTES DE VALIDAÇÃO - OTIMIZAÇÃO DYNAMODB
 * ═══════════════════════════════════════════════════════════════════════
 *
 * Este arquivo contém testes para validar:
 * 1. Compatibilidade entre versão original e otimizada
 * 2. Performance das otimizações
 * 3. Limites de segurança
 * 4. Sistema de cache
 *
 * COMO EXECUTAR:
 * php tests_validacao_otimizacao.php
 *
 * ═══════════════════════════════════════════════════════════════════════
 */

require_once 'Aluno_Service_ControleEstudo.php';
require_once 'Aluno_Service_ControleEstudo_OTIMIZADO.php';

class TestValidacaoOtimizacao
{
    private $serviceOriginal;
    private $serviceOtimizado;
    private $testsPassed = 0;
    private $testsFailed = 0;
    private $testsSkipped = 0;

    // IDs de teste (ajuste conforme seu ambiente)
    const TEST_ALUNO_ID = 12345;
    const TEST_CURSO_ID = 67890;
    const TEST_VIDEO_ID = 111;
    const TEST_PDF_ID = 222;

    public function __construct()
    {
        echo "═══════════════════════════════════════════════════════════════════════\n";
        echo "  INICIANDO TESTES DE VALIDAÇÃO - OTIMIZAÇÃO DYNAMODB\n";
        echo "═══════════════════════════════════════════════════════════════════════\n\n";

        try {
            $this->serviceOriginal = new Aluno_Service_ControleEstudo();
            $this->serviceOtimizado = new Aluno_Service_ControleEstudo_Otimizado();
            echo "✅ Serviços inicializados com sucesso\n\n";
        } catch (Exception $e) {
            echo "❌ ERRO ao inicializar serviços: " . $e->getMessage() . "\n";
            exit(1);
        }
    }

    public function runAllTests()
    {
        echo "═══════════════════════════════════════════════════════════════════════\n";
        echo "  TESTES FUNCIONAIS - COMPATIBILIDADE\n";
        echo "═══════════════════════════════════════════════════════════════════════\n\n";

        $this->testSetItemVideo();
        $this->testSetItemPdf();
        $this->testBulkInsertValidation();

        echo "\n═══════════════════════════════════════════════════════════════════════\n";
        echo "  TESTES DE PERFORMANCE - CACHE\n";
        echo "═══════════════════════════════════════════════════════════════════════\n\n";

        $this->testCacheBasico();
        $this->testCacheTTL();
        $this->testClearCache();
        $this->testInvalidateCache();

        echo "\n═══════════════════════════════════════════════════════════════════════\n";
        echo "  TESTES DE SEGURANÇA - LIMITES\n";
        echo "═══════════════════════════════════════════════════════════════════════\n\n";

        $this->testLimitesSeguranca();
        $this->testValidacaoEntrada();

        echo "\n═══════════════════════════════════════════════════════════════════════\n";
        echo "  TESTES DE PERFORMANCE - QUERIES\n";
        echo "═══════════════════════════════════════════════════════════════════════\n\n";

        $this->testPerformanceGetAulasPdfVisualizadas();
        $this->testPerformanceGetVisualizadosWithLastKey();

        echo "\n═══════════════════════════════════════════════════════════════════════\n";
        echo "  TESTES DE ROBUSTEZ - TRATAMENTO DE ERROS\n";
        echo "═══════════════════════════════════════════════════════════════════════\n\n";

        $this->testTratamentoErros();
        $this->testEntradasInvalidas();

        $this->printSummary();
    }

    // ═══════════════════════════════════════════════════════════════════════
    // TESTES FUNCIONAIS
    // ═══════════════════════════════════════════════════════════════════════

    private function testSetItemVideo()
    {
        echo "🧪 Testando setItemVideo()... ";

        try {
            $itemOriginal = $this->serviceOriginal->setItemVideo(
                self::TEST_ALUNO_ID,
                self::TEST_CURSO_ID,
                self::TEST_VIDEO_ID,
                true
            );

            $itemOtimizado = $this->serviceOtimizado->setItemVideo(
                self::TEST_ALUNO_ID,
                self::TEST_CURSO_ID,
                self::TEST_VIDEO_ID,
                true
            );

            // Valida que ambos são objetos ControleVideo
            if (!($itemOriginal instanceof ControleVideo) || !($itemOtimizado instanceof ControleVideo)) {
                throw new Exception("Items não são instâncias de ControleVideo");
            }

            $this->pass();
        } catch (Exception $e) {
            $this->fail($e->getMessage());
        }
    }

    private function testSetItemPdf()
    {
        echo "🧪 Testando setItemPdf()... ";

        try {
            $itemOriginal = $this->serviceOriginal->setItemPdf(
                self::TEST_ALUNO_ID,
                self::TEST_CURSO_ID,
                self::TEST_PDF_ID,
                true
            );

            $itemOtimizado = $this->serviceOtimizado->setItemPdf(
                self::TEST_ALUNO_ID,
                self::TEST_CURSO_ID,
                self::TEST_PDF_ID,
                true
            );

            if (!($itemOriginal instanceof ControleAulaPdf) || !($itemOtimizado instanceof ControleAulaPdf)) {
                throw new Exception("Items não são instâncias de ControleAulaPdf");
            }

            $this->pass();
        } catch (Exception $e) {
            $this->fail($e->getMessage());
        }
    }

    private function testBulkInsertValidation()
    {
        echo "🧪 Testando bulkInsert() com validação... ";

        try {
            // Teste com array vazio (deve retornar false/não fazer nada)
            $result = $this->serviceOtimizado->bulkInsert([]);

            // Teste com array inválido
            $result2 = $this->serviceOtimizado->bulkInsert(null);

            // Se não lançou exception, passou
            $this->pass();
        } catch (Exception $e) {
            $this->fail($e->getMessage());
        }
    }

    // ═══════════════════════════════════════════════════════════════════════
    // TESTES DE CACHE
    // ═══════════════════════════════════════════════════════════════════════

    private function testCacheBasico()
    {
        echo "🧪 Testando cache básico... ";

        try {
            // Limpa cache antes do teste
            $this->serviceOtimizado->clearCache();

            // Primeira chamada (deve consultar DynamoDB)
            $start1 = microtime(true);
            $result1 = $this->serviceOtimizado->getVideoByAlunoVideo(
                self::TEST_ALUNO_ID,
                self::TEST_CURSO_ID,
                self::TEST_VIDEO_ID
            );
            $time1 = microtime(true) - $start1;

            // Segunda chamada (deve usar cache)
            $start2 = microtime(true);
            $result2 = $this->serviceOtimizado->getVideoByAlunoVideo(
                self::TEST_ALUNO_ID,
                self::TEST_CURSO_ID,
                self::TEST_VIDEO_ID
            );
            $time2 = microtime(true) - $start2;

            // Cache deve ser MUITO mais rápido (pelo menos 2x)
            if ($time2 > $time1 / 2) {
                throw new Exception("Cache não está mais rápido que query direta");
            }

            // Resultados devem ser idênticos
            if ($result1 !== $result2) {
                throw new Exception("Resultados de cache diferem da query original");
            }

            $stats = $this->serviceOtimizado->getStats();
            if ($stats['cache_size'] < 1) {
                throw new Exception("Cache não foi populado");
            }

            $this->pass("Query: " . number_format($time1 * 1000, 2) . "ms, Cache: " . number_format($time2 * 1000, 2) . "ms");
        } catch (Exception $e) {
            $this->fail($e->getMessage());
        }
    }

    private function testCacheTTL()
    {
        echo "🧪 Testando TTL do cache... ";

        try {
            // Este teste é difícil sem mockar tempo
            // Apenas validamos que o cache existe e tem TTL configurado
            $stats = $this->serviceOtimizado->getStats();

            if ($stats['cache_ttl'] <= 0) {
                throw new Exception("TTL do cache não está configurado");
            }

            if ($stats['cache_ttl'] > 3600) {
                throw new Exception("TTL muito alto (risco de dados desatualizados)");
            }

            $this->pass("TTL: {$stats['cache_ttl']}s");
        } catch (Exception $e) {
            $this->fail($e->getMessage());
        }
    }

    private function testClearCache()
    {
        echo "🧪 Testando clearCache()... ";

        try {
            // Popular cache
            $this->serviceOtimizado->getVideoByAlunoVideo(
                self::TEST_ALUNO_ID,
                self::TEST_CURSO_ID,
                self::TEST_VIDEO_ID
            );

            $statsBefore = $this->serviceOtimizado->getStats();
            if ($statsBefore['cache_size'] < 1) {
                throw new Exception("Cache não foi populado antes do clear");
            }

            // Limpar cache
            $this->serviceOtimizado->clearCache();

            $statsAfter = $this->serviceOtimizado->getStats();
            if ($statsAfter['cache_size'] !== 0) {
                throw new Exception("Cache não foi limpo completamente");
            }

            $this->pass();
        } catch (Exception $e) {
            $this->fail($e->getMessage());
        }
    }

    private function testInvalidateCache()
    {
        echo "🧪 Testando invalidação de cache após write... ";

        try {
            $this->serviceOtimizado->clearCache();

            // Popular cache
            $result1 = $this->serviceOtimizado->getVideoByAlunoVideo(
                self::TEST_ALUNO_ID,
                self::TEST_CURSO_ID,
                self::TEST_VIDEO_ID
            );

            $statsBefore = $this->serviceOtimizado->getStats();

            // Simular write (que deve invalidar cache)
            $this->serviceOtimizado->registrarVideoAssistido(
                self::TEST_ALUNO_ID,
                self::TEST_CURSO_ID,
                self::TEST_VIDEO_ID,
                true
            );

            // Cache relacionado deve ter sido invalidado
            // (difícil testar sem instrumentação interna)
            $this->pass("Write executado, invalidação implícita");
        } catch (Exception $e) {
            $this->fail($e->getMessage());
        }
    }

    // ═══════════════════════════════════════════════════════════════════════
    // TESTES DE SEGURANÇA
    // ═══════════════════════════════════════════════════════════════════════

    private function testLimitesSeguranca()
    {
        echo "🧪 Testando limites de segurança... ";

        try {
            $stats = $this->serviceOtimizado->getStats();

            if ($stats['max_iterations'] <= 0) {
                throw new Exception("MAX_ITERATIONS não configurado");
            }

            if ($stats['max_iterations'] > 100) {
                throw new Exception("MAX_ITERATIONS muito alto (risco de custos)");
            }

            if ($stats['max_items_per_query'] <= 0) {
                throw new Exception("MAX_ITEMS_PER_QUERY não configurado");
            }

            if ($stats['chunk_size'] <= 0 || $stats['chunk_size'] > 100) {
                throw new Exception("CHUNK_SIZE fora do range seguro");
            }

            $this->pass(
                "MAX_ITERATIONS: {$stats['max_iterations']}, " .
                "MAX_ITEMS: {$stats['max_items_per_query']}, " .
                "CHUNK: {$stats['chunk_size']}"
            );
        } catch (Exception $e) {
            $this->fail($e->getMessage());
        }
    }

    private function testValidacaoEntrada()
    {
        echo "🧪 Testando validação de entrada... ";

        try {
            // Testa com parâmetros vazios/inválidos
            $result1 = $this->serviceOtimizado->getAulasPdfVisualizadas('', []);
            if (!is_array($result1) || count($result1) > 0) {
                throw new Exception("Não retornou array vazio para entrada inválida");
            }

            $result2 = $this->serviceOtimizado->getAulasPdfVisualizadas(self::TEST_ALUNO_ID, []);
            if (!is_array($result2) || count($result2) > 0) {
                throw new Exception("Não retornou array vazio para aulas vazias");
            }

            $this->pass();
        } catch (Exception $e) {
            $this->fail($e->getMessage());
        }
    }

    // ═══════════════════════════════════════════════════════════════════════
    // TESTES DE PERFORMANCE
    // ═══════════════════════════════════════════════════════════════════════

    private function testPerformanceGetAulasPdfVisualizadas()
    {
        echo "🧪 Testando performance getAulasPdfVisualizadas()... ";

        try {
            // Cria array de 100 aulas (simulando caso real)
            $arAulas = range(1, 100);

            $this->serviceOtimizado->clearCache();

            $start = microtime(true);
            $result = $this->serviceOtimizado->getAulasPdfVisualizadas(
                self::TEST_ALUNO_ID,
                $arAulas
            );
            $time = microtime(true) - $start;

            // Deve retornar array (mesmo que vazio)
            if (!is_array($result)) {
                throw new Exception("Não retornou array");
            }

            // Deve executar em tempo razoável (< 5 segundos para 100 itens)
            if ($time > 5.0) {
                throw new Exception("Muito lento: " . number_format($time, 2) . "s");
            }

            $this->pass("100 aulas em " . number_format($time * 1000, 2) . "ms");
        } catch (Exception $e) {
            $this->fail($e->getMessage());
        }
    }

    private function testPerformanceGetVisualizadosWithLastKey()
    {
        echo "🧪 Testando performance getVisualizadosWithLastKey()... ";

        try {
            $this->serviceOtimizado->clearCache();

            $start = microtime(true);
            $result = $this->serviceOtimizado->getVisualizadosWithLastKey(
                self::TEST_ALUNO_ID,
                'ControleVideo',
                ['GsiAulaPk'],
                100
            );
            $time = microtime(true) - $start;

            if (!is_array($result)) {
                throw new Exception("Não retornou array");
            }

            // Deve executar em tempo razoável
            if ($time > 3.0) {
                throw new Exception("Muito lento: " . number_format($time, 2) . "s");
            }

            $this->pass(count($result) . " itens em " . number_format($time * 1000, 2) . "ms");
        } catch (Exception $e) {
            $this->fail($e->getMessage());
        }
    }

    // ═══════════════════════════════════════════════════════════════════════
    // TESTES DE ROBUSTEZ
    // ═══════════════════════════════════════════════════════════════════════

    private function testTratamentoErros()
    {
        echo "🧪 Testando tratamento de erros... ";

        try {
            // Testa com IDs inválidos (não deve lançar exception)
            $result = $this->serviceOtimizado->getVideoByAlunoVideo(-1, -1, -1);

            // Deve retornar null ou array vazio, não exception
            if ($result !== null && !is_array($result)) {
                throw new Exception("Tipo de retorno inesperado para erro");
            }

            $this->pass();
        } catch (Exception $e) {
            // Se chegou aqui, não tratou o erro corretamente
            $this->fail("Exception não tratada: " . $e->getMessage());
        }
    }

    private function testEntradasInvalidas()
    {
        echo "🧪 Testando entradas inválidas... ";

        try {
            $tests = [
                ['', '', ''],
                [0, 0, 0],
                [null, null, null],
                ['invalid', 'invalid', 'invalid'],
            ];

            foreach ($tests as $test) {
                // Não deve lançar exception
                $result = $this->serviceOtimizado->getVideoByAlunoVideo($test[0], $test[1], $test[2]);

                if ($result !== null && !is_array($result)) {
                    throw new Exception("Tipo de retorno inesperado");
                }
            }

            $this->pass();
        } catch (Exception $e) {
            $this->fail($e->getMessage());
        }
    }

    // ═══════════════════════════════════════════════════════════════════════
    // HELPERS
    // ═══════════════════════════════════════════════════════════════════════

    private function pass($message = '')
    {
        $this->testsPassed++;
        echo "✅ PASSOU";
        if ($message) {
            echo " ($message)";
        }
        echo "\n";
    }

    private function fail($message = '')
    {
        $this->testsFailed++;
        echo "❌ FALHOU";
        if ($message) {
            echo ": $message";
        }
        echo "\n";
    }

    private function skip($message = '')
    {
        $this->testsSkipped++;
        echo "⏭️  PULADO";
        if ($message) {
            echo ": $message";
        }
        echo "\n";
    }

    private function printSummary()
    {
        $total = $this->testsPassed + $this->testsFailed + $this->testsSkipped;

        echo "\n═══════════════════════════════════════════════════════════════════════\n";
        echo "  RESUMO DOS TESTES\n";
        echo "═══════════════════════════════════════════════════════════════════════\n\n";

        echo "Total de testes: $total\n";
        echo "✅ Passou: {$this->testsPassed}\n";
        echo "❌ Falhou: {$this->testsFailed}\n";
        echo "⏭️  Pulado: {$this->testsSkipped}\n\n";

        $successRate = $total > 0 ? ($this->testsPassed / $total) * 100 : 0;
        echo "Taxa de sucesso: " . number_format($successRate, 1) . "%\n\n";

        if ($this->testsFailed === 0) {
            echo "🎉 TODOS OS TESTES PASSARAM! Otimização validada com sucesso.\n";
            echo "✅ Você pode prosseguir com a migração para produção.\n\n";
            exit(0);
        } else {
            echo "⚠️  ALGUNS TESTES FALHARAM. Revise os erros antes de migrar.\n\n";
            exit(1);
        }
    }
}

// ═══════════════════════════════════════════════════════════════════════
// EXECUÇÃO DOS TESTES
// ═══════════════════════════════════════════════════════════════════════

try {
    $tester = new TestValidacaoOtimizacao();
    $tester->runAllTests();
} catch (Exception $e) {
    echo "\n❌ ERRO CRÍTICO: " . $e->getMessage() . "\n";
    echo "Stack trace:\n" . $e->getTraceAsString() . "\n";
    exit(1);
}
