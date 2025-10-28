document.addEventListener('DOMContentLoaded', () => {
    const tipoSelect = document.getElementById('tipoProblema');
    const telefoneInput = document.getElementById('telefone');
    const nomeClienteInput = document.getElementById('nomeCliente');
    const nomeEstabelecimentoInput = document.getElementById('nomeEstabelecimento');
    const formAtendimento = document.getElementById('formAtendimento');
    const mensagem = document.getElementById('mensagem');

    const btnHistorico = document.getElementById('btnHistorico');
    const modalHistorico = document.getElementById('modalHistorico');
    const fecharModal = document.querySelector('.fechar');
    const btnFiltrar = document.getElementById('btnFiltrar');
    const tabelaHistoricoBody = document.querySelector('#tabelaHistorico tbody');

    // --- Carregar tipos de problema ---
    fetch('/tipos_problema.json')
        .then(resp => {
            if (!resp.ok) throw new Error('Erro ao carregar tipos de problema');
            return resp.json();
        })
        .then(tipos => {
            tipoSelect.innerHTML = '';
            tipos.forEach(tipo => {
                const option = document.createElement('option');
                option.value = tipo;
                option.textContent = tipo;
                tipoSelect.appendChild(option);
            });
        })
        .catch(err => {
            console.error(err);
            mensagem.textContent = 'Falha ao carregar os tipos de problema.';
        });

    // --- Buscar cliente pelo telefone ---
    telefoneInput.addEventListener('blur', () => {
        const telefone = telefoneInput.value.trim();
        if (!telefone) return;

        fetch(`/cliente?telefone=${encodeURIComponent(telefone)}`)
            .then(resp => resp.json())
            .then(data => {
                if (data.exists) {
                    nomeClienteInput.value = data.nome_cliente;
                    nomeEstabelecimentoInput.value = data.nome_estabelecimento;
                }
            })
            .catch(err => console.error('Erro ao buscar cliente:', err));
    });

    // --- Cadastrar atendimento ---
    formAtendimento.addEventListener('submit', e => {
        e.preventDefault();

        const payload = {
            telefone: telefoneInput.value,
            nome_estabelecimento: nomeEstabelecimentoInput.value,
            nome_cliente: nomeClienteInput.value,
            descricao: document.getElementById('descricao').value,
            tipo_problema: tipoSelect.value
        };

        fetch('/atendimento', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(payload)
        })
        .then(resp => {
            if (resp.ok) {
                mensagem.textContent = 'Atendimento cadastrado com sucesso!';
                formAtendimento.reset();
            } else {
                mensagem.textContent = 'Erro ao cadastrar atendimento.';
            }
        })
        .catch(err => console.error(err));
    });

    // --- Abrir modal histórico ---
    btnHistorico.addEventListener('click', () => {
        modalHistorico.style.display = 'block';
    });

    fecharModal.addEventListener('click', () => {
        modalHistorico.style.display = 'none';
        tabelaHistoricoBody.innerHTML = '';
    });

    window.addEventListener('click', e => {
        if (e.target == modalHistorico) {
            modalHistorico.style.display = 'none';
            tabelaHistoricoBody.innerHTML = '';
        }
    });

    // --- Filtrar histórico ---
    btnFiltrar.addEventListener('click', () => {
		const filtros = {};

		// Pega os valores dos inputs
		const dataInicioInput = document.getElementById('dataInicio').value;
		const dataFimInput = document.getElementById('dataFim').value;

		if (dataInicioInput) {
			// Adiciona início do dia: 00:00:00
			filtros.dataInicio = `${dataInicioInput} 00:00:00`;
		}
		if (dataFimInput) {
			// Adiciona fim do dia: 23:59:59
			filtros.dataFim = `${dataFimInput} 23:59:59`;
		}

		// Outros filtros
		const telefone = document.getElementById('filtroTelefone').value.trim();
		const estabelecimento = document.getElementById('filtroEstabelecimento').value.trim();
		const usuario = document.getElementById('filtroUsuario').value.trim();

		if (telefone) filtros.telefone = telefone;
		if (estabelecimento) filtros.estabelecimento = estabelecimento;
		if (usuario) filtros.usuario = usuario;

		const params = new URLSearchParams(filtros);
        /*const params = new URLSearchParams({
            dataInicio: document.getElementById('dataInicio').value,
            dataFim: document.getElementById('dataFim').value,
            telefone: document.getElementById('filtroTelefone').value.trim(),
            estabelecimento: document.getElementById('filtroEstabelecimento').value.trim(),
			usuario: document.getElementById('filtroUsuario').value.trim()
        });*/
		
		// Remove os campos vazios
		/*const params = new URLSearchParams();
		for (const key in filtros) {
			if (filtros[key]) {
            params.append(key, filtros[key]);
			}
		}*/

		fetch(`/historico?${params.toString()}`)
            .then(resp => resp.json())
            .then(data => {
                tabelaHistoricoBody.innerHTML = '';
                if (data.length === 0) {
                    tabelaHistoricoBody.innerHTML = '<tr><td colspan="7">Nenhum atendimento encontrado.</td></tr>';
                    return;
                }
                data.forEach(item => {
                    const tr = document.createElement('tr');
                    tr.innerHTML = `
						<td>${item.usuario_nome}</td>
                        <td>${item.datahora}</td>
                        <td>${item.telefone}</td>
                        <td>${item.nome_cliente}</td>
                        <td>${item.nome_estabelecimento}</td>
                        <td>${item.tipo_problema}</td>
                        <td>${item.descricao}</td>
                    `;
                    tabelaHistoricoBody.appendChild(tr);
                });
            })
            .catch(err => console.error('Erro ao buscar histórico:', err));
		});
	});
	
	function atualizarTotaisDia() {
    fetch('/totais_dia')
        .then(resp => resp.json())
        .then(data => {
            document.getElementById('total-usuario').textContent = data.total_usuario;
            document.getElementById('total-geral').textContent = data.total_geral;
        })
        .catch(err => console.error('Erro ao buscar totais do dia:', err));
}

		// Atualiza ao carregar a página
		document.addEventListener('DOMContentLoaded', atualizarTotaisDia);

		// Opcional: atualizar a cada 1 minuto
		setInterval(atualizarTotaisDia, 60000);
