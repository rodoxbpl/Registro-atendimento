from flask import Flask, request, jsonify, render_template, send_from_directory, redirect, url_for
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
import psycopg2
import os
from datetime import datetime, date
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'Trindade@9389'  # troque por algo seguro

# --- Conexão com o banco PostgreSQL ---
DATABASE_URL = os.getenv("DATABASE_URL")

def get_db_connection():
    return psycopg2.connect(DATABASE_URL, sslmode="require")


# --- Inicialização do banco ---
def init_db():
    with get_db_connection() as conn:
        c = conn.cursor()
        # Tabela de usuários
        c.execute('''
            CREATE TABLE IF NOT EXISTS usuarios (
                id SERIAL PRIMARY KEY,
                nome TEXT NOT NULL,
                usuario TEXT UNIQUE NOT NULL,
                senha TEXT NOT NULL
            )
        ''')
        # Clientes
        c.execute('''
            CREATE TABLE IF NOT EXISTS clientes (
                id SERIAL PRIMARY KEY,
                telefone TEXT UNIQUE,
                nome_cliente TEXT,
                nome_estabelecimento TEXT
            )
        ''')
        # Atendimentos
        c.execute('''
            CREATE TABLE IF NOT EXISTS atendimentos (
                id SERIAL PRIMARY KEY,
                datahora TIMESTAMP NOT NULL,
                telefone TEXT,
                nome_cliente TEXT,
                nome_estabelecimento TEXT,
                tipo_problema TEXT,
                descricao TEXT,
                usuario_id INTEGER REFERENCES usuarios(id)
            )
        ''')
        conn.commit()


# --- Flask-Login Config ---
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"


class Usuario(UserMixin):
    def __init__(self, id, nome, usuario, senha):
        self.id = id
        self.nome = nome
        self.usuario = usuario
        self.senha = senha


@login_manager.user_loader
def load_user(user_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, nome, usuario, senha FROM usuarios WHERE id = %s", (user_id,))
    row = cur.fetchone()
    conn.close()
    if row:
        return Usuario(*row)
    return None


# --- Rotas de login/logout ---
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        usuario = request.form["usuario"]
        senha = request.form["senha"]

        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT id, nome, usuario, senha FROM usuarios WHERE usuario = %s", (usuario,))
        row = cur.fetchone()
        conn.close()

        if row and check_password_hash(row[3], senha):
            user = Usuario(*row)
            login_user(user)
            return redirect(url_for("index"))
        else:
            return render_template("login.html", erro="Usuário ou senha incorretos.")
    return render_template("login.html")


@app.route("/registrar", methods=["GET", "POST"])
@login_required
def registrar():
    if request.method == "POST":
        nome = request.form["nome"]
        usuario = request.form["usuario"]
        senha = request.form["senha"]
        senha_hash = generate_password_hash(senha)

        try:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("INSERT INTO usuarios (nome, usuario, senha) VALUES (%s, %s, %s)",
                        (nome, usuario, senha_hash))
            conn.commit()
            conn.close()
            return redirect(url_for("login"))
        except psycopg2.IntegrityError:
            return render_template("registrar.html", erro="Este nome de usuário já está em uso.")
    return render_template("registrar.html")


@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for("login"))


# --- Página principal protegida ---
@app.route("/")
@login_required
def index():
    return render_template("index.html", usuario=current_user.nome)


# --- Tipos de problema ---
@app.route('/tipos_problema.json')
@login_required
def tipos_problema():
    return send_from_directory('.', 'tipos_problema.json')


# --- Cadastrar atendimento ---
@app.route('/atendimento', methods=['POST'])
@login_required
def atendimento():
    data = request.get_json()
    datahora = datetime.now()

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO atendimentos 
        (datahora, telefone, nome_cliente, nome_estabelecimento, tipo_problema, descricao, usuario_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, (
        datahora,
        data.get('telefone', ''),
        data.get('nome_cliente', ''),
        data.get('nome_estabelecimento', ''),
        data.get('tipo_problema', ''),
        data.get('descricao', ''),
        current_user.id
    ))
    conn.commit()
    conn.close()
    return jsonify({"ok": True, "datahora": datahora.strftime("%Y-%m-%d %H:%M:%S")})


# --- Histórico ---
@app.route('/historico')
@login_required
def historico():
    data_inicio = request.args.get('dataInicio')
    data_fim = request.args.get('dataFim')
    telefone = request.args.get('telefone')
    estabelecimento = request.args.get('estabelecimento')
    usuario = request.args.get('usuario')

    conn = get_db_connection()
    cur = conn.cursor()

    query = """
        SELECT a.*, u.nome as usuario_nome
        FROM atendimentos a
        LEFT JOIN usuarios u ON a.usuario_id = u.id
        WHERE 1=1
    """
    params = []

    if data_inicio:
        query += " AND a.datahora >= %s"
        params.append(data_inicio)
    if data_fim:
        query += " AND a.datahora <= %s"
        params.append(data_fim)
    if telefone:
        query += " AND a.telefone ILIKE %s"
        params.append(f"%{telefone}%")
    if estabelecimento:
        query += " AND a.nome_estabelecimento ILIKE %s"
        params.append(f"%{estabelecimento}%")
    if usuario:
        query += " AND u.nome ILIKE %s"
        params.append(f"%{usuario}%")

    query += " ORDER BY a.datahora DESC"

    cur.execute(query, params)
    rows = cur.fetchall()
    colnames = [desc[0] for desc in cur.description]
    conn.close()

    return jsonify([dict(zip(colnames, row)) for row in rows])


# --- Buscar cliente por telefone ---
@app.route('/cliente')
@login_required
def cliente():
    telefone = request.args.get('telefone', '').strip()
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT nome_cliente, nome_estabelecimento 
        FROM atendimentos 
        WHERE telefone = %s 
        ORDER BY datahora DESC 
        LIMIT 1
    """, (telefone,))
    row = cur.fetchone()
    conn.close()
    if row:
        return jsonify({"exists": True, "nome_cliente": row[0], "nome_estabelecimento": row[1]})
    return jsonify({"exists": False})


# --- Criar usuário (inicialização) ---
@app.route('/criar_usuario', methods=['POST'])
def criar_usuario():
    data = request.get_json()
    nome = data.get("nome")
    usuario = data.get("usuario")
    senha = generate_password_hash(data.get("senha"))

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO usuarios (nome, usuario, senha) VALUES (%s, %s, %s)", (nome, usuario, senha))
    conn.commit()
    conn.close()
    return jsonify({"ok": True, "mensagem": "Usuário criado com sucesso."})


# --- Totais do dia ---
@app.route('/totais_dia')
@login_required
def totais_dia():
    try:
        usuario_id = current_user.id
        hoje_inicio = datetime.combine(date.today(), datetime.min.time())
        hoje_fim = datetime.combine(date.today(), datetime.max.time())

        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT COUNT(*) FROM atendimentos
            WHERE usuario_id = %s AND datahora BETWEEN %s AND %s
        """, (usuario_id, hoje_inicio, hoje_fim))
        total_usuario = cur.fetchone()[0]

        cur.execute("""
            SELECT COUNT(*) FROM atendimentos
            WHERE datahora BETWEEN %s AND %s
        """, (hoje_inicio, hoje_fim))
        total_geral = cur.fetchone()[0]

        conn.close()

        return jsonify({
            'total_usuario': total_usuario,
            'total_geral': total_geral
        })

    except Exception as e:
        print("Erro no /totais_dia:", e)
        return jsonify({'error': str(e)}), 500


# --- Inicialização ---
if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=False)
