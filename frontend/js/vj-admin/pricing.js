(function () {
    const fees = {
        preco_pix: 0,
        preco_debito: 1.37,
        preco_credito_vista: 3.15,
        preco_credito_2x: 5.39,
        preco_credito_3x: 6.12,
        preco_credito_4x: 6.85,
        preco_credito_5x: 7.57,
        preco_credito_6x: 8.28,
        preco_credito_7x: 8.99,
        preco_credito_8x: 9.69,
        preco_credito_9x: 10.38,
        preco_credito_10x: 11.06,
        preco_credito_11x: 11.74,
        preco_credito_12x: 12.40,
    };

    const labels = {
        preco_pix: 'Pix',
        preco_debito: 'Debito',
        preco_credito_vista: 'Credito 1x',
        preco_credito_2x: 'Credito 2x',
        preco_credito_3x: 'Credito 3x',
        preco_credito_4x: 'Credito 4x',
        preco_credito_5x: 'Credito 5x',
        preco_credito_6x: 'Credito 6x',
        preco_credito_7x: 'Credito 7x',
        preco_credito_8x: 'Credito 8x',
        preco_credito_9x: 'Credito 9x',
        preco_credito_10x: 'Credito 10x',
        preco_credito_11x: 'Credito 11x',
        preco_credito_12x: 'Credito 12x',
    };

    function roundMoney(value) {
        return Math.round((Number(value) + Number.EPSILON) * 100) / 100;
    }

    function calculate(custoPeca, custoEmbalagem = 9.34, markup = 2) {
        const piece = Number(custoPeca || 0);
        const packaging = Number(custoEmbalagem || 0);
        const markupValue = Number(markup || 2);
        const custoTotal = roundMoney(piece + packaging);
        const result = {
            custo_peca: roundMoney(piece),
            custo_embalagem: roundMoney(packaging),
            custo_total: custoTotal,
            markup: markupValue,
        };
        Object.entries(fees).forEach(([field, fee]) => {
            result[field] = roundMoney((custoTotal * markupValue) / (1 - fee / 100));
        });
        result.lucro_pix = roundMoney(result.preco_pix - custoTotal);
        result.margem_pix = result.preco_pix ? result.lucro_pix / result.preco_pix : 0;
        return result;
    }

    window.VJAdminPricing = { fees, labels, calculate };
})();
