#!/bin/bash

###############################################################################
# SCRIPT DE VALIDAÇÃO - OTIMIZAÇÃO DYNAMODB
###############################################################################
#
# Este script executa todos os testes e validações necessárias
# para garantir que a otimização está funcionando corretamente.
#
# USO:
#   chmod +x validar_otimizacao.sh
#   ./validar_otimizacao.sh
#
###############################################################################

set -e  # Exit on error

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Funções de output
info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

success() {
    echo -e "${GREEN}✅ $1${NC}"
}

warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

error() {
    echo -e "${RED}❌ $1${NC}"
}

header() {
    echo ""
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════════════${NC}"
    echo ""
}

###############################################################################
# VERIFICAÇÕES INICIAIS
###############################################################################

header "VALIDAÇÃO DE OTIMIZAÇÃO DYNAMODB"

info "Verificando ambiente..."

# Verifica PHP
if ! command -v php &> /dev/null; then
    error "PHP não encontrado. Por favor, instale o PHP."
    exit 1
fi

PHP_VERSION=$(php -v | head -n 1 | cut -d " " -f 2 | cut -d "." -f 1)
if [ "$PHP_VERSION" -lt 7 ]; then
    warning "PHP versão < 7 detectado. Recomendado PHP 7.4+"
fi

success "PHP instalado: $(php -v | head -n 1)"

# Verifica arquivos necessários
FILES=(
    "Aluno_Service_ControleEstudo_OTIMIZADO.php"
    "OTIMIZACAO_DYNAMODB.md"
    "tests_validacao_otimizacao.php"
    "calculadora_economia_dynamodb.php"
    "README_OTIMIZACAO.md"
)

info "Verificando arquivos necessários..."
MISSING=0
for FILE in "${FILES[@]}"; do
    if [ ! -f "$FILE" ]; then
        error "Arquivo não encontrado: $FILE"
        MISSING=1
    fi
done

if [ $MISSING -eq 1 ]; then
    error "Arquivos faltando. Por favor, verifique o pacote de otimização."
    exit 1
fi

success "Todos os arquivos necessários presentes"

###############################################################################
# TESTES AUTOMATIZADOS
###############################################################################

header "EXECUTANDO TESTES AUTOMATIZADOS"

info "Iniciando suite de testes..."
echo ""

if php tests_validacao_otimizacao.php; then
    success "Todos os testes passaram!"
    TESTS_PASSED=1
else
    error "Alguns testes falharam. Revise o output acima."
    TESTS_PASSED=0
fi

###############################################################################
# CALCULADORA DE ECONOMIA
###############################################################################

header "CALCULANDO ECONOMIA ESTIMADA"

warning "IMPORTANTE: Ajuste as constantes em calculadora_economia_dynamodb.php com seus dados reais"
echo ""

info "Executando calculadora..."
echo ""

php calculadora_economia_dynamodb.php

###############################################################################
# CHECKLIST MANUAL
###############################################################################

header "CHECKLIST MANUAL"

echo "Por favor, verifique os seguintes itens:"
echo ""

echo "  [ ] Li a documentação completa (OTIMIZACAO_DYNAMODB.md)"
echo "  [ ] Li o README de implementação (README_OTIMIZACAO.md)"
echo "  [ ] Ajustei as constantes da calculadora com dados reais"
echo "  [ ] Entendi as mudanças e impactos"
echo "  [ ] Tenho acesso ao CloudWatch para monitoramento"
echo "  [ ] Tenho estratégia de rollback definida"
echo "  [ ] Tenho feature flag implementado (recomendado)"
echo ""

read -p "Todos os itens acima foram verificados? (s/N) " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Ss]$ ]]; then
    warning "Por favor, complete o checklist antes de prosseguir."
    exit 0
fi

###############################################################################
# RECOMENDAÇÕES
###############################################################################

header "PRÓXIMOS PASSOS"

if [ $TESTS_PASSED -eq 1 ]; then
    success "Validação concluída com sucesso!"
    echo ""
    info "Recomendações:"
    echo ""
    echo "  1. 📖 Leia a documentação completa:"
    echo "     cat OTIMIZACAO_DYNAMODB.md"
    echo ""
    echo "  2. 🧪 Deploy em ambiente de desenvolvimento:"
    echo "     - Copie Aluno_Service_ControleEstudo_OTIMIZADO.php"
    echo "     - Teste com dados reais"
    echo "     - Compare resultados com versão original"
    echo ""
    echo "  3. 🚀 Deploy gradual em produção:"
    echo "     - Implemente feature flag"
    echo "     - Ative para 10% do tráfego"
    echo "     - Monitore por 24h"
    echo "     - Aumente gradualmente"
    echo ""
    echo "  4. 📊 Monitore métricas no CloudWatch:"
    echo "     - ConsumedReadCapacityUnits (deve reduzir 60-80%)"
    echo "     - UserErrors (deve permanecer estável)"
    echo "     - Latency (deve melhorar)"
    echo ""
    echo "  5. 🎉 Após 1 semana de sucesso:"
    echo "     - Remova classe antiga"
    echo "     - Documente economia real"
    echo "     - Celebre! 🎊"
    echo ""
else
    error "Testes falharam. Por favor, revise os erros antes de prosseguir."
    echo ""
    info "Ações recomendadas:"
    echo "  - Verifique os erros nos testes"
    echo "  - Confirme que o DynamoDB está acessível"
    echo "  - Ajuste as constantes de teste com IDs válidos"
    echo "  - Execute novamente este script"
    echo ""
fi

###############################################################################
# INFORMAÇÕES ÚTEIS
###############################################################################

header "INFORMAÇÕES ÚTEIS"

echo "📚 Documentação:"
echo "   - OTIMIZACAO_DYNAMODB.md: Análise completa e guia de migração"
echo "   - README_OTIMIZACAO.md: Início rápido e referência"
echo ""

echo "🛠️  Arquivos:"
echo "   - Aluno_Service_ControleEstudo_OTIMIZADO.php: Classe otimizada"
echo "   - tests_validacao_otimizacao.php: Suite de testes"
echo "   - calculadora_economia_dynamodb.php: Calculadora de ROI"
echo ""

echo "💰 Economia estimada: 60-80% em custos de RCU"
echo "⏱️  Tempo de implementação: 4 horas"
echo "📈 ROI: Positivo no primeiro mês"
echo ""

success "Validação completa! ✨"
echo ""
