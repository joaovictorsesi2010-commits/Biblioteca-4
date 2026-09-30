import fdb
from flask import Flask, render_template, request, flash, redirect, url_for, send_file
from flask_bcrypt import Bcrypt
from fpdf import FPDF

app = Flask(__name__)

app.config['SECRET_KEY'] = '*****'

bcrypt = Bcrypt(app)

host = 'localhost'
database = r'C:\Users\Aluno\Downloads\BANCO (1)\BANCO.FDB'
user = 'sysdba'
password = 'sysdba'

con = fdb.connect(host=host, database=database, user=user, password=password)


@app.route('/')
def index():
    cursor = con.cursor()

    cursor.execute("""SELECT l.id_livros, l.TITULO, l.AUTOR, l.ANO_PUBLICACAO
                      FROM LIVROS l""")

    livros = cursor.fetchall()
    cursor.close()

    return render_template("index.html", livros=livros)


@app.route('/novo')
def novo():
    return render_template('novo.html')


@app.route('/criar', methods=['POST'])
def criar():
    titulo = request.form['titulo']
    autor = request.form['autor']
    ano_publicacao = request.form['ano_publicacao']

    cursor = con.cursor()

    try:
        cursor.execute("""SELECT 1 FROM livros WHERE titulo = ?""", [titulo])

        if cursor.fetchone():
            flash('Erro: Livro já existe no banco')
            return redirect(url_for('novo'))

        cursor.execute("""INSERT INTO livros (titulo, autor, ano_publicacao)
                          VALUES (?, ?, ?) RETURNING id_livros""",
                       (titulo, autor, ano_publicacao))

        id_livros = cursor.fetchone()[0]

        con.commit()

        arquivo = request.files['imagem']
        arquivo.save(f"uploads/livros/{id_livros}.jpg")

        flash('Livro cadastrado com sucesso!')
        return redirect(url_for('index'))

    except Exception as e:
        flash(f'Ocorreu um erro: {e}')
        con.rollback()

    finally:
        cursor.close()


@app.route('/editar/<int:id>', methods=['GET', 'POST'])
def editar(id):
    cursor = con.cursor()

    try:
        cursor.execute("""SELECT id_livros, titulo, autor, ano_publicacao
                          FROM LIVROS
                          WHERE id_livros = ?""", [id])

        livro = cursor.fetchone()

        if not livro:
            flash('Livro não encontrado')
            return redirect(url_for('index'))

        if request.method == 'POST':
            titulo = request.form['titulo']
            autor = request.form['autor']
            ano_publicacao = request.form['ano_publicacao']

            cursor.execute("""UPDATE LIVROS
                              SET titulo = ?, autor = ?, ano_publicacao = ?
                              WHERE id_livros = ?""",
                           (titulo, autor, ano_publicacao, id))

            con.commit()

            flash('Livro editado com sucesso!')
            return redirect(url_for('index'))

        return render_template('editar.html', livro=livro)

    except Exception as e:
        flash(f'Deu erro aqui! -> {e}')
        con.rollback()

    finally:
        cursor.close()


@app.route('/deletar/<int:id>')
def deletar(id):
    cursor = con.cursor()

    try:
        cursor.execute("""DELETE FROM LIVROS WHERE id_livros = ?""", (id,))

        con.commit()

        flash("O livro foi deletado")
        return redirect(url_for("index"))

    except Exception as e:
        flash(f'Algo deu errado -> {e}')
        con.rollback()

    finally:
        cursor.close()


@app.route('/cadastrar', methods=['GET', 'POST'])
def cadastrar():
    if request.method == 'POST':
        nome = request.form['nome']
        senha = request.form['senha']
        email = request.form['email']

        if len(senha) < 8:
            flash('A senha deve ter pelo menos 8 caracteres')
            return redirect(url_for('cadastrar'))

        if senha.islower():
            flash('A senha deve ter pelo menos uma letra maiúscula')
            return redirect(url_for('cadastrar'))

        cursor = con.cursor()

        try:
            cursor.execute("""SELECT 1 FROM USUARIOS WHERE nome = ?""", [nome])

            if cursor.fetchone():
                flash('Erro: Usuário já existe')
                return redirect(url_for('cadastrar'))

            senha_hash = bcrypt.generate_password_hash(senha).decode('utf-8')

            cursor.execute("""INSERT INTO USUARIOS (NOME, SENHA, EMAIL)
                              VALUES (?, ?, ?)""",
                           (nome, senha_hash, email))

            con.commit()

            flash('Cadastro realizado')
            return redirect(url_for('login'))

        except Exception as e:
            flash(f'Ocorreu um erro: {e}')
            con.rollback()

        finally:
            cursor.close()

    return render_template('cadastro.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        nome = request.form['nome']
        senha = request.form['senha']

        cursor = con.cursor()

        try:
            cursor.execute("""SELECT senha FROM USUARIOS WHERE nome = ?""", [nome])

            usuario = cursor.fetchone()

            if usuario:
                senha_hash = usuario[0]

                if bcrypt.check_password_hash(senha_hash, senha):
                    flash('Login feito')
                    return redirect(url_for('index'))

            flash('Nome ou senha incorretos')
            return redirect(url_for('login'))

        except Exception as e:
            flash(f'Ocorreu um erro: {e}')
            con.rollback()

        finally:
            cursor.close()

    return render_template('login.html')


@app.route('/index')
def relatorio():
    cursor = con.cursor()

    try:
        cursor.execute("""SELECT id_livros, TITULO, AUTOR, ANO_PUBLICACAO
                          FROM LIVROS""")

        livros = cursor.fetchall()

    finally:
        cursor.close()

    pdf = FPDF()

    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    pdf.set_font("Arial", style='B', size=16)
    pdf.cell(200, 10, "Relatório de Livros", ln=True, align='C')

    pdf.ln(5)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(5)

    pdf.set_font("Arial", size=12)

    for livro in livros:
        pdf.cell(
            200,
            10,
            f"ID: {livro[0]} - {livro[1]} - {livro[2]} - {livro[3]}",
            ln=True
        )

    contador_livros = len(livros)

    pdf.ln(10)

    pdf.set_font("Arial", style='B', size=12)

    pdf.cell(
        200,
        10,
        f"Total de livros cadastrados: {contador_livros}",
        ln=True,
        align='C'
    )

    pdf_path = "relatorio_livros.pdf"

    pdf.output(pdf_path)

    return send_file(
        pdf_path,
        as_attachment=True,
        mimetype='application/pdf'
    )


if __name__ == '__main__':
    app.run(debug=True)
