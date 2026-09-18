import psycopg2
from dotenv import load_dotenv
import os

load_dotenv()


def get_connection():
    try:
        conn = psycopg2.connect(
            host=os.getenv("DB_HOST"),
            port=os.getenv("DB_PORT"),
            database=os.getenv("DB_NAME"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
        )
        return conn
    except Exception as ex:
        print("Erro ao conectar ao banco:", ex)
        return None


def init_db():
    """Cria as tabelas (se não existirem) e garante que as vagas 1, 2 e 3 existam."""
    conn = get_connection()
    if not conn:
        return
    try:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS vagas (
                    id SERIAL PRIMARY KEY,
                    numero INTEGER UNIQUE NOT NULL,
                    status BOOLEAN NOT NULL DEFAULT FALSE
                );
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS ocupacoes (
                    id SERIAL PRIMARY KEY,
                    vaga_id INTEGER NOT NULL REFERENCES vagas(id),
                    entrada TIMESTAMP NOT NULL DEFAULT NOW(),
                    saida TIMESTAMP
                );
            """)
            for numero in (1, 2, 3):
                cur.execute("""
                    INSERT INTO vagas (numero, status)
                    VALUES (%s, FALSE)
                    ON CONFLICT (numero) DO NOTHING;
                """, (numero,))
        conn.commit()
        print("Banco inicializado (tabelas + vagas 1-3).")
    except Exception as ex:
        print("Erro ao inicializar banco:", ex)
        conn.rollback()
    finally:
        conn.close()


def atualizar_status_vaga(numero, ocupada):
    """
    Atualiza o status de uma vaga e mantém o histórico em `ocupacoes`.

    - Se a vaga passou de livre -> ocupada: abre um novo registro (entrada = agora).
    - Se a vaga passou de ocupada -> livre: fecha o registro em aberto (saida = agora).
    - Se o estado não mudou (ex: sensor reenviando o mesmo valor), não faz nada.

    Retorna True se algo foi alterado, False caso contrário.
    """
    conn = get_connection()
    if not conn:
        return False
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, status FROM vagas WHERE numero = %s", (numero,))
            row = cur.fetchone()
            if row is None:
                print(f"Vaga {numero} não encontrada no banco (verifique init_db).")
                return False

            vaga_id, status_atual = row

            if status_atual == ocupada:
                return False  # nada mudou, evita duplicar entrada/saída

            cur.execute("UPDATE vagas SET status = %s WHERE id = %s", (ocupada, vaga_id))

            if ocupada:
                cur.execute("""
                    INSERT INTO ocupacoes (vaga_id, entrada)
                    VALUES (%s, NOW())
                """, (vaga_id,))
            else:
                # Postgres não permite UPDATE ... ORDER BY ... LIMIT diretamente,
                # por isso fechamos o registro em aberto mais recente via subquery.
                cur.execute("""
                    UPDATE ocupacoes
                    SET saida = NOW()
                    WHERE id = (
                        SELECT id FROM ocupacoes
                        WHERE vaga_id = %s AND saida IS NULL
                        ORDER BY entrada DESC
                        LIMIT 1
                    )
                """, (vaga_id,))

        conn.commit()
        return True
    except Exception as ex:
        print("Erro ao atualizar status da vaga:", ex)
        conn.rollback()
        return False
    finally:
        conn.close()


def get_vagas_status():
    """Lista as 3 vagas com status atual e, se ocupada, desde quando."""
    conn = get_connection()
    if not conn:
        return []
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT v.numero, v.status, o.entrada
                FROM vagas v
                LEFT JOIN ocupacoes o
                    ON o.vaga_id = v.id AND o.saida IS NULL
                ORDER BY v.numero
            """)
            rows = cur.fetchall()

        return [
            {
                "numero": numero,
                "ocupada": status,
                "entrada": entrada.isoformat() if entrada else None,
            }
            for numero, status, entrada in rows
        ]
    except Exception as ex:
        print("Erro ao buscar vagas:", ex)
        return []
    finally:
        conn.close()


def get_ocupacoes(vaga_numero=None, limite=30):
    """Histórico de entradas/saídas, mais recentes primeiro."""
    conn = get_connection()
    if not conn:
        return []
    try:
        with conn.cursor() as cur:
            if vaga_numero:
                cur.execute("""
                    SELECT v.numero, o.entrada, o.saida
                    FROM ocupacoes o
                    JOIN vagas v ON v.id = o.vaga_id
                    WHERE v.numero = %s
                    ORDER BY o.entrada DESC
                    LIMIT %s
                """, (vaga_numero, limite))
            else:
                cur.execute("""
                    SELECT v.numero, o.entrada, o.saida
                    FROM ocupacoes o
                    JOIN vagas v ON v.id = o.vaga_id
                    ORDER BY o.entrada DESC
                    LIMIT %s
                """, (limite,))
            rows = cur.fetchall()

        historico = []
        for numero, entrada, saida in rows:
            duracao_min = round((saida - entrada).total_seconds() / 60, 1) if saida else None
            historico.append({
                "vaga": numero,
                "entrada": entrada.isoformat() if entrada else None,
                "saida": saida.isoformat() if saida else None,
                "duracao_min": duracao_min,
            })
        return historico
    except Exception as ex:
        print("Erro ao buscar ocupações:", ex)
        return []
    finally:
        conn.close()


def get_taxa_ocupacao():
    """Percentual de vagas ocupadas neste exato momento."""
    conn = get_connection()
    if not conn:
        return {"total": 0, "ocupadas": 0, "taxa": 0}
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM vagas")
            total = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM vagas WHERE status = TRUE")
            ocupadas = cur.fetchone()[0]
        taxa = round((ocupadas / total) * 100, 1) if total else 0
        return {"total": total, "ocupadas": ocupadas, "taxa": taxa}
    except Exception as ex:
        print("Erro ao calcular taxa de ocupação:", ex)
        return {"total": 0, "ocupadas": 0, "taxa": 0}
    finally:
        conn.close()


def get_horarios_pico():
    """Quantidade de entradas por hora do dia (0-23), somando todo o histórico."""
    conn = get_connection()
    if not conn:
        return []
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT EXTRACT(HOUR FROM entrada)::int AS hora, COUNT(*) AS total
                FROM ocupacoes
                GROUP BY hora
                ORDER BY hora
            """)
            rows = cur.fetchall()
        return [{"hora": h, "total": t} for h, t in rows]
    except Exception as ex:
        print("Erro ao calcular horários de pico:", ex)
        return []
    finally:
        conn.close()