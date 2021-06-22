from django.conf import settings
from gsheets.connect import ConnectGS
import pandas as pd
import numpy as np
from core.models import *
from core.utils import (
    get_estado,
    get_tipo_produto,
    get_medida,
    get_produtor_by_name,
    get_produto_by_name,
    get_start_end_this_week,
)
from datetime import datetime as dt
from dateutil.relativedelta import relativedelta
from django_pandas.io import read_frame
from core.enum import TIPO_PRODUTO_CHOICES
from analysis.ranking.ranking import ranking
from analysis import cesta_feia

spreadsheet = settings.SPREADSHEET_ID


def rename_produtores_columns(cols):
    clean_cols = []
    for c_ in cols:
        c = c_.lower()
        if "estado" in c:
            clean_cols.append("estado")
        else:
            clean_cols.append(c)
    return clean_cols


def read_update_produtores(replace=False):
    """Reads produtores data from google sheets and updates database"""

    print("\nReading sheet 'Produtores' from google sheets")
    gs = ConnectGS()
    data = gs.read_sheet(
        sheet_id=spreadsheet,
        worksheet="Produtores",
        range="A:H",
    )
    df = pd.DataFrame().from_dict(data["values"])
    df.columns = df.iloc[0]
    df = df[1:]

    # df.to_csv("produtores.csv")
    df.columns = [c.lower() for c in df.columns]

    df.columns = rename_produtores_columns(df.columns)
    df.remover = df.remover.apply(lambda x: x.lower() == "true")

    if not df.empty and replace:
        Produtor.objects.all().delete()

    print("Updating 'Produtores' Table\n")
    for i, row in df.iterrows():
        if row.remover:
            try:
                Produtor.objects.get(nome=row.produtor).delete()
            except:
                pass
            continue

        provider, created = Produtor.objects.update_or_create(
            nome=row.produtor,
            defaults={
                "email": row.email,
                "estado": get_estado(row.estado),
                "morada": row.morada,
                "concelho": row.concelho,
                "telefone": row.telefone,
            },
        )

        if isinstance(row.produtos, str):

            products = row.produtos.split(",")
            products = [p.strip() for p in products]
            for product in products:
                try:
                    product_obj = Produto.objects.get(nome=product)
                except Produto.DoesNotExist:
                    continue
                provider.produtos.add(product_obj)
    print("\n\nDone!")
    print(len(df), Produtor.objects.all().count())


def rename_produtos_columns(cols):
    clean_cols = []
    for c_ in cols:
        c = c_.lower()
        if "família" in c:
            clean_cols.append("familia")
        elif "quantidade" in c and "pequena" in c:
            clean_cols.append("quantidade_cesta_pequena")
        elif "quantidade" in c and "grande" in c:
            clean_cols.append("quantidade_cesta_grande")
        else:
            clean_cols.append(c)
    return clean_cols


def read_update_produtos(replace=False):
    """Reads produtos data from google sheets and updates database"""

    print("\nReading sheet 'Produtos' from google sheets")
    gs = ConnectGS()
    data = gs.read_sheet(
        sheet_id=spreadsheet,
        worksheet="Produtos",
        range="A:F",
    )
    df = pd.DataFrame().from_dict(data["values"])
    df.columns = df.iloc[0]
    df = df[1:]

    # df.to_csv("produtos.csv")
    df.columns = rename_produtos_columns(df.columns)
    if not df.empty and replace:
        Produto.objects.all().delete()
    print("Updating 'Produto' Table\n")
    for i, row in df.iterrows():
        print(row)

        family_obj, created = FamiliaProduto.objects.get_or_create(nome=row.familia)
        if isinstance(row.quantidade_cesta_pequena, str):
            try:
                row.quantidade_cesta_pequena = float(row.quantidade_cesta_pequena)
            except:
                row.quantidade_cesta_pequena = None

        if isinstance(row.quantidade_cesta_grande, str):
            try:
                row.quantidade_cesta_grande = float(row.quantidade_cesta_grande)
            except:
                row.quantidade_cesta_grande = None

        product_obj, created = Produto.objects.get_or_create(
            familia=family_obj,
            nome=row.produto,
            tipo=get_tipo_produto(row.tipo),
            medida=get_medida(row.medida),
            quantidade_cesta_pequena=row.quantidade_cesta_pequena,
            quantidade_cesta_grande=row.quantidade_cesta_grande,
        )

    print("\n\nDone!")
    print(len(df), Produto.objects.all().count())
    print(len(df.familia.unique()), FamiliaProduto.objects.all().count())


def rename_disponibilidade_columns(cols):
    clean_cols = []
    for c in cols:
        if "data" in c.lower():
            clean_cols.append("data")
        elif "preço" in c.lower():
            clean_cols.append("preco")
        elif "quantidade" in c.lower():
            clean_cols.append("quantidade")
        elif "urgente" in c.lower():
            clean_cols.append("urgente")
        else:
            clean_cols.append(c.lower())
    return clean_cols


def check_bool(u):
    if u:
        if u.lower() == "sim":
            return True
        elif u.lower() == "true":
            return True
    return False


def try_float(x):
    if not x:
        return None
    else:
        return float(x)


def read_update_disponibilidade():
    """Reads isponibilidades data from google sheets and updates database"""

    print("\nReading sheet 'Disponibilidade' from google sheets")
    gs = ConnectGS()
    data = gs.read_sheet(
        sheet_id=spreadsheet,
        worksheet="Disponibilidade",
        range="A:H",
    )
    df = pd.DataFrame().from_dict(data["values"])
    df = df.iloc[7:]
    df.columns = df.iloc[0]
    df = df[1:]
    # df.to_csv("disponibilidade.csv")

    df.columns = rename_disponibilidade_columns(df.columns)
    df = df.loc[~df.produtor.isnull()]
    df.data = pd.to_datetime(df.data)
    df.medida = df.medida.map(get_medida)
    df.quantidade = df.quantidade.map(try_float)
    df.preco = df.preco.map(try_float)
    df.remover = df.remover.map(check_bool)
    df.urgente = df.urgente.map(check_bool)
    print("Updating 'Disponobilidade' Table\n")

    # Delete everything first, so we make sure we dont have any duplicates
    Disponibilidade.objects.all().delete()
    for i, row in df.iterrows():
        print("getting", row.data, row.produtor, row.produto)
        if row.remover:
            continue
        try:
            produto_obj = Produto.objects.get(nome=row.produto)
        except Produto.DoesNotExist:
            print(f"cant find product {row.producto}")
            continue
        try:
            produtor_obj = Produtor.objects.get(nome=row.produtor)
        except Produtor.DoesNotExist:
            print(f"cant find produtor {row.produtor}")
            continue

        Disponibilidade.objects.create(
            data=row.data,
            produto=produto_obj,
            produtor=produtor_obj,
            quantidade=row.quantidade,
            medida=row.medida,
            preco=row.preco,
            urgente=row.urgente,
        ).save()
    print("\n\nDone!")


def calculate_and_update_ranking():
    print("calculating Ranking")
    today = dt.now()
    two_years_ago = today - relativedelta(years=2)
    qs = MapaDeCampo.objects.filter(data__gte=two_years_ago).values(
        "data", "produto__nome", "produtor"
    )
    df = read_frame(qs)
    df.rename(columns={"produto__nome": "produto"}, inplace=True)
    df.data = pd.to_datetime(df.data)
    result = ranking(df)
    if not result:
        print("No data estimated..")
        return False
    Ranking.objects.all().delete()
    for rank in result:
        # rank = result[0]
        produtor = Produtor.objects.get(nome=rank.get("produtor"))
        produto = Produto.objects.get(nome=rank.get("produto"))
        pontuacao = rank.get("pontuacao")
        Ranking.objects.create(produtor=produtor, produto=produto, pontuacao=pontuacao)
    print("Done")
    return True


def calculate_and_update_cestas():
    print("calculating cestas")

    qs = Disponibilidade.objects.all().values(
        "produto__nome",
        "produto__id",
        "produto__familia__nome",
        "produto__tipo",
        "produto__quantidade_cesta_pequena",
        "produto__quantidade_cesta_grande",
        "produtor__nome",
        "produtor__id",
        "quantidade",
        "medida",
        "preco",
        "urgente",
    )
    df = read_frame(qs)
    df.reset_index(inplace=True, drop=True)
    df.produto__tipo = df.produto__tipo.apply(
        lambda x: dict(TIPO_PRODUTO_CHOICES).get(x).lower()
    )

    df["ranking"] = 10
    for i, row in df.iterrows():
        try:
            r = Ranking.objects.get(
                produtor__nome=row.produtor__nome, produto__nome=row.produto__nome
            )
            df.iloc[i, "ranking"] = r
            print("success")
        except:
            continue
    df.rename(
        columns={
            "produto__id": "ID_PRODUTO",
            "produto__nome": "produto",
            "produto__familia__nome": "familia",
            "produto__tipo": "tipo",
            "produto__quantidade_cesta_pequena": "quantidade_cesta_pequena",
            "produto__quantidade_cesta_grande": "quantidade_cesta_grande",
            "produtor__nome": "produtor",
            "produtor__id": "ID_PRODUTOR",
        },
        inplace=True,
    )

    sucess, result = cesta_feia.main(df)
    if not sucess:
        print(result)
        return
    print(f"Updating {len(result)} cestas..")
    for i, res in enumerate(result):
        print(f"cesta {i + 1}")
        df = res["df"]
        df = df[
            [
                "produto",
                "produtor",
                "quantidade_cesta_pequena",
                "quantidade_cesta_grande",
                "medida",
                "preco",
                "yij",
            ]
        ]
        df.produtor = df.produtor.map(get_produtor_by_name)
        df.produto = df.produto.map(get_produto_by_name)
        df.medida = df.medida.map(get_medida)
        date_start, _ = get_start_end_this_week()
        cesta, _ = Cesta.objects.get_or_create(
            data=date_start,
            preco_pequena=res["stats"]["pequena"]["preco"],
            peso_pequena=res["stats"]["pequena"]["peso"],
            preco_grande=res["stats"]["grande"]["preco"],
            peso_grande=res["stats"]["grande"]["peso"],
        )
        for i, row in df.iterrows():
            obj, created = ConteudoCesta.objects.get_or_create(
                produto=row.produto,
                produtor=row.produtor,
                quantidade_pequena=row.quantidade_cesta_pequena,
                quantidade_grande=row.quantidade_cesta_grande,
                medida=row.medida,
                preco_unitario=3,
                produto_extra=int(row.yij) == 1,
            )
            cesta.conteudo.add(obj)
