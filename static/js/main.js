(() => {
    "use strict";

    const grid = document.getElementById("vagas-grid");
    const liveIndicator = document.getElementById("live-indicator");
    const liveText = document.getElementById("live-text");
    const taxaNumero = document.getElementById("taxa-numero");
    const taxaPreenchimento = document.getElementById("taxa-preenchimento");
    const taxaSub = document.getElementById("taxa-sub");
    const graficoHorarios = document.getElementById("grafico-horarios");
    const historicoCorpo = document.getElementById("historico-corpo");

    // guarda a hora de entrada de cada vaga ocupada para os cronômetros ao vivo
    const entradasAtivas = {};

    function marcarOnline(online) {
        liveIndicator.classList.toggle("is-online", online);
        liveIndicator.classList.toggle("is-offline", !online);
        liveText.textContent = online ? "ao vivo" : "sem conexão com a API";
    }

    async function buscarJson(url) {
        const resp = await fetch(url);
        if (!resp.ok) throw new Error(`${url} -> HTTP ${resp.status}`);
        return resp.json();
    }

    function formatarDuracao(segundosTotais) {
        const segundos = Math.max(0, Math.floor(segundosTotais));
        const h = Math.floor(segundos / 3600);
        const m = Math.floor((segundos % 3600) / 60);
        const s = segundos % 60;
        if (h > 0) return `${h}h${String(m).padStart(2, "0")}m`;
        if (m > 0) return `${m}m${String(s).padStart(2, "0")}s`;
        return `${s}s`;
    }

    function formatarHorario(isoString) {
        if (!isoString) return "—";
        const d = new Date(isoString);
        return d.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });
    }

    // ---------- Cards das vagas ----------

    function renderVagas(vagas) {
        grid.innerHTML = "";
        entradasAtivas.list = vagas;

        vagas.forEach((vaga) => {
            const ocupada = vaga.ocupada;
            const card = document.createElement("article");
            card.className = `vaga-card ${ocupada ? "vaga-card--ocupada" : "vaga-card--livre"}`;

            const led = document.createElement("div");
            led.className = "vaga-card__led";
            led.textContent = vaga.numero;

            const status = document.createElement("p");
            status.className = "vaga-card__status";
            status.textContent = ocupada ? "OCUPADA" : "LIVRE";

            const tempo = document.createElement("p");
            tempo.className = "vaga-card__tempo";
            tempo.dataset.entrada = vaga.entrada || "";
            tempo.textContent = ocupada && vaga.entrada
                ? formatarDuracao((Date.now() - new Date(vaga.entrada)) / 1000)
                : "";

            card.append(led, status, tempo);
            grid.appendChild(card);
        });
    }

    function atualizarCronometros() {
        document.querySelectorAll(".vaga-card__tempo").forEach((el) => {
            const entrada = el.dataset.entrada;
            if (!entrada) return;
            el.textContent = formatarDuracao((Date.now() - new Date(entrada)) / 1000);
        });
    }

    // ---------- Taxa de ocupação ----------

    function renderTaxa(dados) {
        taxaNumero.textContent = `${dados.taxa}%`;
        taxaPreenchimento.style.width = `${dados.taxa}%`;
        taxaSub.textContent = `${dados.ocupadas} de ${dados.total} vagas ocupadas`;
    }

    // ---------- Gráfico de horários de pico (SVG simples) ----------

    function renderGraficoHorarios(dados) {
        const largura = 480;
        const altura = 140;
        const margemInferior = 18;
        const porHora = new Array(24).fill(0);
        dados.forEach((item) => { porHora[item.hora] = item.total; });

        const maximo = Math.max(1, ...porHora);
        const larguraBarra = largura / 24;

        let svg = `<line class="grafico-eixo" x1="0" y1="${altura - margemInferior}" x2="${largura}" y2="${altura - margemInferior}" />`;

        porHora.forEach((total, hora) => {
            const alturaBarra = (total / maximo) * (altura - margemInferior - 10);
            const x = hora * larguraBarra + 1;
            const y = altura - margemInferior - alturaBarra;
            svg += `<rect class="grafico-barra" x="${x}" y="${y}" width="${larguraBarra - 2}" height="${alturaBarra}" rx="2"></rect>`;
            if (hora % 3 === 0) {
                svg += `<text class="grafico-rotulo" x="${x}" y="${altura - 4}">${hora}h</text>`;
            }
        });

        graficoHorarios.innerHTML = svg;
    }

    // ---------- Histórico ----------

    function renderHistorico(itens) {
        historicoCorpo.innerHTML = "";

        if (itens.length === 0) {
            const linha = document.createElement("tr");
            linha.className = "historico__vazio";
            linha.innerHTML = `<td colspan="4">Nenhuma movimentação registrada ainda.</td>`;
            historicoCorpo.appendChild(linha);
            return;
        }

        itens.forEach((item) => {
            const linha = document.createElement("tr");
            const duracaoTexto = item.saida
                ? formatarDuracao(item.duracao_min * 60)
                : "";

            linha.innerHTML = `
                <td>Vaga ${item.vaga}</td>
                <td>${formatarHorario(item.entrada)}</td>
                <td>${item.saida ? formatarHorario(item.saida) : '<span class="tag-aberta">em andamento</span>'}</td>
                <td>${duracaoTexto}</td>
            `;
            historicoCorpo.appendChild(linha);
        });
    }

    // ---------- Polling ----------

    async function ciclo() {
        try {
            const vagas = await buscarJson("/api/vagas");
            renderVagas(vagas);
            marcarOnline(true);
        } catch (err) {
            console.error(err);
            marcarOnline(false);
        }
    }

    async function cicloTaxa() {
        try {
            const dados = await buscarJson("/api/estatisticas/taxa-ocupacao");
            renderTaxa(dados);
        } catch (err) {
            console.error(err);
        }
    }

    async function cicloHorarios() {
        try {
            const dados = await buscarJson("/api/estatisticas/horarios-pico");
            renderGraficoHorarios(dados);
        } catch (err) {
            console.error(err);
        }
    }

    async function cicloHistorico() {
        try {
            const dados = await buscarJson("/api/ocupacoes?limite=20");
            renderHistorico(dados);
        } catch (err) {
            console.error(err);
        }
    }

    function iniciar() {
        ciclo();
        cicloTaxa();
        cicloHorarios();
        cicloHistorico();

        setInterval(ciclo, 3000);
        setInterval(cicloTaxa, 5000);
        setInterval(cicloHistorico, 5000);
        setInterval(cicloHorarios, 30000);
        setInterval(atualizarCronometros, 1000);
    }

    document.addEventListener("DOMContentLoaded", iniciar);
})();