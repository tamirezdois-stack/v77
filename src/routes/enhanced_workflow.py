#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ARQV30 Enhanced v3.0 - Enhanced Workflow Routes
Rotas para o workflow aprimorado em 3 etapas
"""

import logging
import time
import uuid
import asyncio
import os
import glob
from datetime import datetime
from typing import Dict, Any  # Import necessário para Dict e Any
from flask import Blueprint, request, jsonify, send_file
from services.real_search_orchestrator import real_search_orchestrator
from services.viral_content_analyzer import viral_content_analyzer
from services.enhanced_synthesis_engine import enhanced_synthesis_engine
from services.enhanced_module_processor import enhanced_module_processor
from services.comprehensive_report_generator_v3 import comprehensive_report_generator_v3
from services.auto_save_manager import salvar_etapa
# Sistema viral separado
from viral.viral_analyzer import ViralContentAnalyzer

logger = logging.getLogger(__name__)

enhanced_workflow_bp = Blueprint('enhanced_workflow', __name__)

@enhanced_workflow_bp.route('/workflow/step1/start', methods=['POST'])
def start_step1_collection():
    """ETAPA 1: Coleta Massiva de Dados com Screenshots"""
    try:
        data = request.get_json()

        # Gera session_id único
        session_id = f"session_{int(time.time() * 1000)}_{uuid.uuid4().hex[:8]}"

        # Extrai parâmetros
        segmento = data.get('segmento', '').strip()
        produto = data.get('produto', '').strip()
        publico = data.get('publico', '').strip()

        # Validação
        if not segmento:
            return jsonify({"error": "Segmento é obrigatório"}), 400

        # Constrói query de pesquisa
        query_parts = [segmento]
        if produto:
            query_parts.append(produto)
        query_parts.extend(["Brasil", "2024", "mercado"])

        query = " ".join(query_parts)

        # Contexto da análise
        context = {
            "segmento": segmento,
            "produto": produto,
            "publico": publico,
            "query_original": query,
            "etapa": 1,
            "workflow_type": "enhanced_v3"
        }

        logger.info(f"🚀 ETAPA 1 INICIADA - Sessão: {session_id}")
        logger.info(f"🔍 Query: {query}")

        # Salva início da etapa 1
        salvar_etapa("etapa1_iniciada", {
            "session_id": session_id,
            "query": query,
            "context": context,
            "timestamp": datetime.now().isoformat()
        }, categoria="workflow")

        # Executa coleta massiva em thread separada
        def execute_collection():
            try:
                # Executa busca massiva real
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

                try:
                    search_results = loop.run_until_complete(
                        real_search_orchestrator.execute_massive_real_search(
                            query=query,
                            context=context,
                            session_id=session_id
                        )
                    )

                    # Analisa e captura conteúdo viral
                    viral_analysis = loop.run_until_complete(
                        viral_content_analyzer.analyze_and_capture_viral_content(
                            search_results=search_results,
                            session_id=session_id,
                            max_captures=15
                        )
                    )

                    # 🎯 SISTEMA VIRAL SEPARADO - Captura imagens das redes sociais
                    logger.info(f"🖼️ INICIANDO CAPTURA DE IMAGENS VIRAIS - Sessão: {session_id}")
                    viral_images_analysis = loop.run_until_complete(
                        _capture_viral_social_media_images(query, context, session_id)
                    )

                finally:
                    loop.close()

                # Gera relatório de coleta (incluindo imagens virais)
                collection_report = _generate_collection_report(
                    search_results, viral_analysis, session_id, context, viral_images_analysis
                )

                # Salva relatório
                _save_collection_report(collection_report, session_id)

                # Salva resultado da etapa 1
                salvar_etapa("etapa1_concluida", {
                    "session_id": session_id,
                    "search_results": search_results,
                    "viral_analysis": viral_analysis,
                    "viral_images_analysis": viral_images_analysis,
                    "collection_report_generated": True,
                    "timestamp": datetime.now().isoformat()
                }, categoria="workflow")

                logger.info(f"✅ ETAPA 1 CONCLUÍDA - Sessão: {session_id}")

            except Exception as e:
                logger.error(f"❌ Erro na execução da Etapa 1: {e}")
                salvar_etapa("etapa1_erro", {
                    "session_id": session_id,
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                }, categoria="workflow")

        # Inicia execução em background
        import threading
        thread = threading.Thread(target=execute_collection, daemon=True)
        thread.start()

        return jsonify({
            "success": True,
            "session_id": session_id,
            "message": "Etapa 1 iniciada: Coleta massiva de dados",
            "query": query,
            "estimated_duration": "3-5 minutos",
            "next_step": "/api/workflow/step2/start",
            "status_endpoint": f"/api/workflow/status/{session_id}"
        }), 200

    except Exception as e:
        logger.error(f"❌ Erro ao iniciar Etapa 1: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "message": "Falha ao iniciar coleta de dados"
        }), 500

@enhanced_workflow_bp.route('/workflow/step2/start', methods=['POST'])
def start_step2_synthesis():
    """ETAPA 2: Síntese com IA e Busca Ativa"""
    try:
        data = request.get_json()
        session_id = data.get('session_id')

        if not session_id:
            return jsonify({"error": "session_id é obrigatório"}), 400

        logger.info(f"🧠 ETAPA 2 INICIADA - Síntese para sessão: {session_id}")

        # Salva início da etapa 2
        salvar_etapa("etapa2_iniciada", {
            "session_id": session_id,
            "timestamp": datetime.now().isoformat()
        }, categoria="workflow")

        # Executa síntese em thread separada
        def execute_synthesis():
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

                try:
                    # Executa síntese master com busca ativa
                    synthesis_result = loop.run_until_complete(
                        enhanced_synthesis_engine.execute_enhanced_synthesis(
                            session_id=session_id,
                            synthesis_type="master_synthesis"
                        )
                    )

                    # Executa síntese comportamental
                    behavioral_result = loop.run_until_complete(
                        enhanced_synthesis_engine.execute_behavioral_synthesis(session_id)
                    )

                    # Executa síntese de mercado
                    market_result = loop.run_until_complete(
                        enhanced_synthesis_engine.execute_market_synthesis(session_id)
                    )

                finally:
                    loop.close()

                # Salva resultado da etapa 2
                salvar_etapa("etapa2_concluida", {
                    "session_id": session_id,
                    "synthesis_result": synthesis_result,
                    "behavioral_result": behavioral_result,
                    "market_result": market_result,
                    "timestamp": datetime.now().isoformat()
                }, categoria="workflow")

                logger.info(f"✅ ETAPA 2 CONCLUÍDA - Sessão: {session_id}")

            except Exception as e:
                logger.error(f"❌ Erro na execução da Etapa 2: {e}")
                salvar_etapa("etapa2_erro", {
                    "session_id": session_id,
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                }, categoria="workflow")

        # Inicia execução em background
        import threading
        thread = threading.Thread(target=execute_synthesis, daemon=True)
        thread.start()

        return jsonify({
            "success": True,
            "session_id": session_id,
            "message": "Etapa 2 iniciada: Síntese com IA e busca ativa",
            "estimated_duration": "2-4 minutos",
            "next_step": "/api/workflow/step3/start",
            "status_endpoint": f"/api/workflow/status/{session_id}"
        }), 200

    except Exception as e:
        logger.error(f"❌ Erro ao iniciar Etapa 2: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "message": "Falha ao iniciar síntese"
        }), 500

@enhanced_workflow_bp.route('/workflow/step3/start', methods=['POST'])
def start_step3_generation():
    """ETAPA 3: Geração dos 16 Módulos e Relatório Final"""
    try:
        data = request.get_json()
        session_id = data.get('session_id')

        if not session_id:
            return jsonify({"error": "session_id é obrigatório"}), 400

        logger.info(f"📝 ETAPA 3 INICIADA - Geração para sessão: {session_id}")

        # Salva início da etapa 3
        salvar_etapa("etapa3_iniciada", {
            "session_id": session_id,
            "timestamp": datetime.now().isoformat()
        }, categoria="workflow")

        # Executa geração em thread separada
        def execute_generation():
            try:
                # Gera todos os 16 módulos
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

                try:
                    modules_result = loop.run_until_complete(
                        enhanced_module_processor.generate_all_modules(session_id)
                    )
                finally:
                    loop.close()

                # Compila relatório final
                final_report = comprehensive_report_generator_v3.compile_final_markdown_report(session_id)

                # Salva resultado da etapa 3
                salvar_etapa("etapa3_concluida", {
                    "session_id": session_id,
                    "modules_result": modules_result,
                    "final_report": final_report,
                    "timestamp": datetime.now().isoformat()
                }, categoria="workflow")

                logger.info(f"✅ ETAPA 3 CONCLUÍDA - Sessão: {session_id}")
                logger.info(f"📊 {modules_result.get('successful_modules', 0)}/16 módulos gerados")

            except Exception as e:
                logger.error(f"❌ Erro na execução da Etapa 3: {e}")
                salvar_etapa("etapa3_erro", {
                    "session_id": session_id,
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                }, categoria="workflow")

        # Inicia execução em background
        import threading
        thread = threading.Thread(target=execute_generation, daemon=True)
        thread.start()

        return jsonify({
            "success": True,
            "session_id": session_id,
            "message": "Etapa 3 iniciada: Geração de 16 módulos",
            "estimated_duration": "4-6 minutos",
            "modules_to_generate": 16,
            "status_endpoint": f"/api/workflow/status/{session_id}"
        }), 200

    except Exception as e:
        logger.error(f"❌ Erro ao iniciar Etapa 3: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "message": "Falha ao iniciar geração de módulos"
        }), 500

@enhanced_workflow_bp.route('/workflow/complete', methods=['POST'])
def execute_complete_workflow():
    """Executa workflow completo em sequência"""
    try:
        data = request.get_json()

        # Gera session_id único
        session_id = f"session_{int(time.time() * 1000)}_{uuid.uuid4().hex[:8]}"

        logger.info(f"🚀 WORKFLOW COMPLETO INICIADO - Sessão: {session_id}")

        # Executa workflow completo em thread separada
        def execute_full_workflow():
            try:
                # ETAPA 1: Coleta
                logger.info("🌊 Executando Etapa 1: Coleta massiva")

                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

                try:
                    # Constrói query
                    segmento = data.get('segmento', '').strip()
                    produto = data.get('produto', '').strip()
                    query = f"{segmento} {produto} Brasil 2024 mercado".strip()                 
                    context = {
                        "segmento": segmento,
                        "produto": produto,
                        "publico": data.get('publico', ''),
                        "preco": data.get('preco', ''),
                        "objetivo_receita": data.get('objetivo_receita', ''),
                        "workflow_type": "complete"
                    }

                    # Executa busca massiva
                    search_results = loop.run_until_complete(
                        real_search_orchestrator.execute_massive_real_search(
                            query=query,
                            context=context,
                            session_id=session_id
                        )
                    )

                    # Analisa conteúdo viral
                    viral_analysis = loop.run_until_complete(
                        viral_content_analyzer.analyze_and_capture_viral_content(
                            search_results=search_results,
                            session_id=session_id
                        )
                    )

                    # Gera relatório de coleta
                    collection_report = _generate_collection_report(
                        search_results, viral_analysis, session_id, context
                    )
                    _save_collection_report(collection_report, session_id)

                    # ETAPA 2: Síntese
                    logger.info("🧠 Executando Etapa 2: Síntese com IA")

                    synthesis_result = loop.run_until_complete(
                        enhanced_synthesis_engine.execute_enhanced_synthesis(session_id)
                    )

                    # ETAPA 3: Geração de módulos
                    logger.info("📝 Executando Etapa 3: Geração de módulos")

                    modules_result = loop.run_until_complete(
                        enhanced_module_processor.generate_all_modules(session_id)
                    )

                    # Compila relatório final
                    final_report = comprehensive_report_generator_v3.compile_final_markdown_report(session_id)

                finally:
                    loop.close()

                # Salva resultado final
                salvar_etapa("workflow_completo", {
                    "session_id": session_id,
                    "search_results": search_results,
                    "viral_analysis": viral_analysis,
                    "synthesis_result": synthesis_result,
                    "modules_result": modules_result,
                    "final_report": final_report,
                    "timestamp": datetime.now().isoformat()
                }, categoria="workflow")

                logger.info(f"✅ WORKFLOW COMPLETO CONCLUÍDO - Sessão: {session_id}")

            except Exception as e:
                logger.error(f"❌ Erro no workflow completo: {e}")
                salvar_etapa("workflow_erro", {
                    "session_id": session_id,
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                }, categoria="workflow")

        # Inicia execução em background
        import threading
        thread = threading.Thread(target=execute_full_workflow, daemon=True)
        thread.start()

        return jsonify({
            "success": True,
            "session_id": session_id,
            "message": "Workflow completo iniciado",
            "estimated_total_duration": "8-15 minutos",
            "steps": [
                "Etapa 1: Coleta massiva (3-5 min)",
                "Etapa 2: Síntese com IA (2-4 min)", 
                "Etapa 3: Geração de módulos (4-6 min)"
            ],
            "status_endpoint": f"/api/workflow/status/{session_id}"
        }), 200

    except Exception as e:
        logger.error(f"❌ Erro ao iniciar workflow completo: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@enhanced_workflow_bp.route('/workflow/status/<session_id>', methods=['GET'])
def get_workflow_status(session_id):
    """Obtém status do workflow"""
    try:
        # Verifica arquivos salvos para determinar status

        status = {
            "session_id": session_id,
            "current_step": 0,
            "step_status": {
                "step1": "pending",
                "step2": "pending", 
                "step3": "pending"
            },
            "progress_percentage": 0,
            "estimated_remaining": "Calculando...",
            "last_update": datetime.now().isoformat()
        }

        # Verifica se etapa 1 foi concluída
        if os.path.exists(f"analyses_data/{session_id}/relatorio_coleta.md"):
            status["step_status"]["step1"] = "completed"
            status["current_step"] = 1
            status["progress_percentage"] = 33

        # Verifica se etapa 2 foi concluída
        if os.path.exists(f"analyses_data/{session_id}/resumo_sintese.json"):
            status["step_status"]["step2"] = "completed"
            status["current_step"] = 2
            status["progress_percentage"] = 66

        # Verifica se etapa 3 foi concluída
        if os.path.exists(f"analyses_data/{session_id}/relatorio_final.md"):
            status["step_status"]["step3"] = "completed"
            status["current_step"] = 3
            status["progress_percentage"] = 100
            status["estimated_remaining"] = "Concluído"

        # Verifica se há erros
        error_files = [
            f"relatorios_intermediarios/workflow/etapa1_erro*{session_id}*",
            f"relatorios_intermediarios/workflow/etapa2_erro*{session_id}*",
            f"relatorios_intermediarios/workflow/etapa3_erro*{session_id}*"
        ]

        for pattern in error_files:
            if glob.glob(pattern):
                status["error"] = "Erro detectado em uma das etapas"
                break

        return jsonify(status), 200

    except Exception as e:
        logger.error(f"❌ Erro ao obter status: {e}")
        return jsonify({
            "session_id": session_id,
            "error": str(e),
            "status": "error"
        }), 500

@enhanced_workflow_bp.route('/workflow/results/<session_id>', methods=['GET'])
def get_workflow_results(session_id):
    """Obtém resultados do workflow"""
    try:

        results = {
            "session_id": session_id,
            "available_files": [],
            "final_report_available": False,
            "modules_generated": 0,
            "screenshots_captured": 0
        }

        # Verifica relatório final
        final_report_path = f"analyses_data/{session_id}/relatorio_final.md"
        if os.path.exists(final_report_path):
            results["final_report_available"] = True
            results["final_report_path"] = final_report_path

        # Conta módulos gerados
        modules_dir = f"analyses_data/{session_id}/modules"
        if os.path.exists(modules_dir):
            modules = [f for f in os.listdir(modules_dir) if f.endswith('.md')]
            results["modules_generated"] = len(modules)
            results["modules_list"] = modules

        # Conta screenshots
        files_dir = f"analyses_data/files/{session_id}"
        if os.path.exists(files_dir):
            screenshots = [f for f in os.listdir(files_dir) if f.endswith('.png')]
            results["screenshots_captured"] = len(screenshots)
            results["screenshots_list"] = screenshots

        # Lista todos os arquivos disponíveis
        session_dir = f"analyses_data/{session_id}"
        if os.path.exists(session_dir):
            for root, dirs, files in os.walk(session_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    relative_path = os.path.relpath(file_path, session_dir)
                    results["available_files"].append({
                        "name": file,
                        "path": relative_path,
                        "size": os.path.getsize(file_path),
                        "type": file.split('.')[-1] if '.' in file else 'unknown'
                    })

        return jsonify(results), 200

    except Exception as e:
        logger.error(f"❌ Erro ao obter resultados: {e}")
        return jsonify({
            "session_id": session_id,
            "error": str(e)
        }), 500

@enhanced_workflow_bp.route('/workflow/download/<session_id>/<file_type>', methods=['GET'])
def download_workflow_file(session_id, file_type):
    """Download de arquivos do workflow"""
    try:
        # Define o caminho base (sem src/)
        base_path = os.path.join("analyses_data", session_id)

        if file_type == "final_report":
            # Tenta primeiro o relatorio_final.md, depois o completo como fallback
            file_path = os.path.join(base_path, "relatorio_final.md")
            if not os.path.exists(file_path):
                file_path = os.path.join(base_path, "relatorio_final_completo.md")
            filename = f"relatorio_final_{session_id}.md"
        elif file_type == "complete_report":
            file_path = os.path.join(base_path, "relatorio_final_completo.md")
            filename = f"relatorio_completo_{session_id}.md"
        else:
            return jsonify({"error": "Tipo de relatório inválido"}), 400

        if not os.path.exists(file_path):
            return jsonify({"error": "Arquivo não encontrado"}), 404

        return send_file(
            file_path,
            as_attachment=True,
            download_name=filename
        )

    except Exception as e:
        logger.error(f"❌ Erro no download: {e}")
        return jsonify({"error": str(e)}), 500

# --- Funções auxiliares ---
def _generate_collection_report(
    search_results: Dict[str, Any], 
    viral_analysis: Dict[str, Any], 
    session_id: str, 
    context: Dict[str, Any],
    viral_images_analysis: Dict[str, Any] = None
) -> str:
    """Gera relatório consolidado de coleta"""

    # Função auxiliar para formatar números com segurança
    def safe_format_int(value):
        try:
            # Tenta converter para int e formatar com separador de milhar
            return f"{int(value):,}"
        except (ValueError, TypeError):
            # Se falhar, retorna 'N/A' ou o valor original como string
            return str(value) if value is not None else 'N/A'

    report = f"""# RELATÓRIO DE COLETA MASSIVA - ARQV30 Enhanced v3.0

**Sessão:** {session_id}  
**Query:** {search_results.get('query', 'N/A')}  
**Iniciado em:** {search_results.get('search_started', 'N/A')}  
**Duração:** {search_results.get('statistics', {}).get('search_duration', 0):.2f} segundos

---

## RESUMO DA COLETA MASSIVA

### Estatísticas Gerais:
- **Total de Fontes:** {search_results.get('statistics', {}).get('total_sources', 0)}
- **URLs Únicas:** {search_results.get('statistics', {}).get('unique_urls', 0)}
- **Conteúdo Extraído:** {safe_format_int(search_results.get('statistics', {}).get('content_extracted', 0))} caracteres
- **Provedores Utilizados:** {len(search_results.get('providers_used', []))}
- **Conteúdo Viral Identificado:** {len(viral_analysis.get('viral_content_identified', []))}
- **Screenshots Capturados:** {len(viral_analysis.get('screenshots_captured', []))}

### Provedores Utilizados:
"""
    providers = search_results.get('providers_used', [])
    if providers:
        report += "\n".join(f"- {provider}" for provider in providers) + "\n\n"
    else:
        report += "- Nenhum provedor listado\n\n"

    report += "---\n\n## RESULTADOS DE BUSCA WEB\n\n"

    # Adiciona resultados web
    web_results = search_results.get('web_results', [])
    if web_results:
        for i, result in enumerate(web_results[:15], 1):
            report += f"### {i}. {result.get('title', 'Sem título')}\n\n"
            report += f"**URL:** {result.get('url', 'N/A')}  \n"
            report += f"**Fonte:** {result.get('source', 'N/A')}  \n"
            report += f"**Relevância:** {result.get('relevance_score', 0):.2f}/1.0  \n"
            snippet = result.get('snippet', 'N/A')
            report += f"**Resumo:** {snippet[:200]}{'...' if len(snippet) > 200 else ''}  \n\n"
    else:
        report += "Nenhum resultado web encontrado.\n\n"

    # Adiciona resultados do YouTube
    youtube_results = search_results.get('youtube_results', [])
    if youtube_results:
        report += "---\n\n## RESULTADOS DO YOUTUBE\n\n"
        for i, result in enumerate(youtube_results[:10], 1):
            report += f"### {i}. {result.get('title', 'Sem título')}\n\n"
            report += f"**Canal:** {result.get('channel', 'N/A')}  \n"
            report += f"**Views:** {safe_format_int(result.get('view_count', 'N/A'))}  \n"
            report += f"**Likes:** {safe_format_int(result.get('like_count', 'N/A'))}  \n"
            report += f"**Comentários:** {safe_format_int(result.get('comment_count', 'N/A'))}  \n"
            report += f"**Score Viral:** {result.get('viral_score', 0):.2f}/10  \n"
            report += f"**URL:** {result.get('url', 'N/A')}  \n\n"
    else:
        report += "---\n\n## RESULTADOS DO YOUTUBE\n\nNenhum resultado do YouTube encontrado.\n\n"

    # Adiciona resultados de redes sociais
    social_results = search_results.get('social_results', [])
    if social_results:
        report += "---\n\n## RESULTADOS DE REDES SOCIAIS\n\n"
        for i, result in enumerate(social_results[:10], 1):
            report += f"### {i}. {result.get('title', 'Sem título')}\n\n"
            report += f"**Plataforma:** {result.get('platform', 'N/A').title() if result.get('platform') else 'N/A'}  \n"
            report += f"**Autor:** {result.get('author', 'N/A')}  \n"
            report += f"**Engajamento:** {result.get('viral_score', 0):.2f}/10  \n"
            report += f"**URL:** {result.get('url', 'N/A')}  \n"
            content = result.get('content', 'N/A')
            report += f"**Conteúdo:** {content[:150]}{'...' if len(content) > 150 else ''}  \n\n"
    else:
        report += "---\n\n## RESULTADOS DE REDES SOCIAIS\n\nNenhum resultado de rede social encontrado.\n\n"

    # Adiciona screenshots capturados
    screenshots = viral_analysis.get('screenshots_captured', [])
    if screenshots:
        report += "---\n\n## EVIDÊNCIAS VISUAIS CAPTURADAS\n\n"
        for i, screenshot in enumerate(screenshots, 1):
            report += f"### Screenshot {i}: {screenshot.get('title', 'Sem título')}\n\n"
            report += f"**Plataforma:** {screenshot.get('platform', 'N/A').title() if screenshot.get('platform') else 'N/A'}  \n"
            report += f"**Score Viral:** {screenshot.get('viral_score', 0):.2f}/10  \n"
            report += f"**URL Original:** {screenshot.get('url', 'N/A')}  \n"

            # Métricas de engajamento - CORRIGIDO AQUI
            metrics = screenshot.get('content_metrics', {})
            if metrics:
                # Usa a função auxiliar para formatar com segurança
                if 'views' in metrics:
                    report += f"**Views:** {safe_format_int(metrics['views'])}  \n"
                if 'likes' in metrics:
                    report += f"**Likes:** {safe_format_int(metrics['likes'])}  \n"
                if 'comments' in metrics:
                    report += f"**Comentários:** {safe_format_int(metrics['comments'])}  \n"
            
            # Verifica se o caminho da imagem existe antes de adicioná-lo
            img_path = screenshot.get('relative_path', '')
            # Ajuste o caminho base conforme a estrutura do seu projeto
            full_img_path = os.path.join("analyses_data", "files", session_id, os.path.basename(img_path)) 
            if img_path and os.path.exists(full_img_path):
                 report += f"![Screenshot {i}]({img_path})  \n\n"
            elif img_path: # Se o caminho existir, mas o arquivo não, mostra o caminho
                 report += f"![Screenshot {i}]({img_path}) *(Imagem não encontrada localmente)*  \n\n"
            else:
                 report += "*Imagem não disponível.*  \n\n"
    else:
        report += "---\n\n## EVIDÊNCIAS VISUAIS CAPTURADAS\n\nNenhum screenshot foi capturado.\n\n"

    # 🎯 NOVA SEÇÃO: IMAGENS VIRAIS DAS REDES SOCIAIS
    if viral_images_analysis:
        report += "---\n\n## 🖼️ IMAGENS VIRAIS DAS REDES SOCIAIS\n\n"
        
        total_content = viral_images_analysis.get('total_content', 0)
        platforms = viral_images_analysis.get('platforms', {})
        screenshots_captured = viral_images_analysis.get('screenshots_captured', 0)
        avg_virality = viral_images_analysis.get('average_virality_score', 0)
        
        report += f"**Total de Conteúdos Analisados:** {total_content}  \n"
        report += f"**Screenshots Capturados:** {screenshots_captured}  \n"
        report += f"**Score Médio de Viralidade:** {avg_virality:.2f}/10  \n\n"
        
        # Breakdown por plataforma
        report += "### Distribuição por Plataforma\n\n"
        for platform, count in platforms.items():
            emoji = {"instagram": "📸", "youtube": "🎥", "facebook": "📘"}.get(platform, "📱")
            report += f"- **{emoji} {platform.title()}:** {count} conteúdos  \n"
        
        # Top hashtags
        top_hashtags = viral_images_analysis.get('top_hashtags', [])
        if top_hashtags:
            report += "\n### 🏷️ Hashtags Mais Populares\n\n"
            for hashtag, count in top_hashtags[:5]:
                report += f"- **#{hashtag}:** {count} ocorrências  \n"
        
        report += "\n"
    else:
        report += "---\n\n## 🖼️ IMAGENS VIRAIS DAS REDES SOCIAIS\n\nNenhuma imagem viral foi capturada.\n\n"

    # Adiciona contexto da análise
    report += "---\n\n## CONTEXTO DA ANÁLISE\n\n"
    context_items_added = False
    for key, value in context.items():
        if value: # Só adiciona se o valor não for vazio/falso
            report += f"**{key.replace('_', ' ').title()}:** {value}  \n"
            context_items_added = True
    if not context_items_added:
         report += "Nenhum contexto adicional fornecido.\n"
    report += f"\n---\n\n*Relatório gerado automaticamente em {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}*"

    return report

def _save_collection_report(report_content: str, session_id: str):
    """Salva relatório de coleta"""
    try:
        session_dir = f"analyses_data/{session_id}"
        os.makedirs(session_dir, exist_ok=True)

        report_path = f"{session_dir}/relatorio_coleta.md"
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report_content)

        logger.info(f"✅ Relatório de coleta salvo: {report_path}")

    except Exception as e:
        logger.error(f"❌ Erro ao salvar relatório de coleta: {e}")
        # Opcional: Re-raise a exception se quiser que o erro pare a execução da etapa
        # raise 

# --- SISTEMA VIRAL SEPARADO ---

async def _capture_viral_social_media_images(query: str, context: str, session_id: str) -> Dict[str, Any]:
    """
    🎯 CAPTURA IMAGENS VIRAIS DAS REDES SOCIAIS
    Integra o sistema viral separado para baixar imagens do Instagram, Facebook e YouTube
    """
    try:
        logger.info(f"🖼️ Iniciando captura de imagens virais para: {query}")
        
        # Inicializa o analisador viral
        async with ViralContentAnalyzer() as viral_analyzer:
            
            # Lista para armazenar todos os conteúdos virais
            all_viral_content = []
            
            # 1. INSTAGRAM - Busca por hashtags relacionadas
            logger.info("📸 Analisando Instagram...")
            instagram_hashtags = [
                query.replace(" ", ""),
                f"{query.replace(' ', '')}brasil",
                f"{query.replace(' ', '')}2024",
                "sustentabilidade",
                "meioambiente",
                "ecologia"
            ]
            
            for hashtag in instagram_hashtags[:3]:  # Limita a 3 hashtags
                instagram_content = await viral_analyzer.analyze_instagram_content(
                    hashtag=hashtag, 
                    limit=5
                )
                all_viral_content.extend(instagram_content)
                logger.info(f"📸 Instagram #{hashtag}: {len(instagram_content)} conteúdos encontrados")
            
            # 2. YOUTUBE - Busca por vídeos virais
            logger.info("🎥 Analisando YouTube...")
            youtube_queries = [
                query,
                f"{query} viral",
                f"{query} tendência",
                f"{query} 2024"
            ]
            
            for yt_query in youtube_queries[:2]:  # Limita a 2 queries
                youtube_content = await viral_analyzer.analyze_youtube_content(
                    query=yt_query,
                    limit=10
                )
                all_viral_content.extend(youtube_content)
                logger.info(f"🎥 YouTube '{yt_query}': {len(youtube_content)} vídeos encontrados")
            
            # 3. FACEBOOK - Análise simulada (API limitada)
            logger.info("📘 Analisando Facebook...")
            facebook_content = await viral_analyzer.analyze_facebook_content(
                query=query,
                limit=5
            )
            all_viral_content.extend(facebook_content)
            logger.info(f"📘 Facebook: {len(facebook_content)} posts encontrados")
            
            # Processa e salva os resultados
            viral_summary = {
                "total_content": len(all_viral_content),
                "platforms": {
                    "instagram": len([c for c in all_viral_content if c.platform == "Instagram"]),
                    "youtube": len([c for c in all_viral_content if c.platform == "YouTube"]),
                    "facebook": len([c for c in all_viral_content if c.platform == "Facebook"])
                },
                "screenshots_captured": len([c for c in all_viral_content if c.screenshot_path]),
                "average_virality_score": sum(c.virality_score for c in all_viral_content) / len(all_viral_content) if all_viral_content else 0,
                "top_hashtags": _extract_top_hashtags(all_viral_content),
                "session_id": session_id,
                "timestamp": datetime.now().isoformat()
            }
            
            # Salva os dados
            _save_viral_images_data(all_viral_content, viral_summary, session_id)
            
            # 🚫 DOWNLOAD DE IMAGENS PÚBLICAS DESABILITADO - APENAS REDES SOCIAIS
            logger.info("🚫 Download de imagens públicas (Unsplash/Pixabay) DESABILITADO")
            logger.info("📱 Usando APENAS imagens de redes sociais (Instagram/Facebook/YouTube)")
            
            # Atualiza o resumo sem imagens públicas
            viral_summary["public_images_downloaded"] = 0
            viral_summary["total_images"] = viral_summary['screenshots_captured']
            
            logger.info(f"✅ CAPTURA VIRAL CONCLUÍDA: {len(all_viral_content)} conteúdos, {viral_summary.get('total_images', viral_summary['screenshots_captured'])} imagens totais")
            
            return viral_summary
            
    except Exception as e:
        logger.error(f"❌ Erro na captura de imagens virais: {e}")
        return {
            "total_content": 0,
            "platforms": {"instagram": 0, "youtube": 0, "facebook": 0},
            "screenshots_captured": 0,
            "error": str(e),
            "session_id": session_id,
            "timestamp": datetime.now().isoformat()
        }

def _extract_top_hashtags(viral_content_list) -> list:
    """Extrai as hashtags mais populares"""
    hashtag_count = {}
    for content in viral_content_list:
        for hashtag in content.hashtags:
            hashtag_count[hashtag] = hashtag_count.get(hashtag, 0) + 1
    
    return sorted(hashtag_count.items(), key=lambda x: x[1], reverse=True)[:10]

def _save_viral_images_data(viral_content_list, summary, session_id: str):
    """Salva os dados das imagens virais"""
    try:
        # Diretório para salvar
        save_dir = os.path.join("analyses_data", session_id, "viral_images")
        os.makedirs(save_dir, exist_ok=True)
        
        # Converte conteúdo viral para dict
        viral_data = []
        for content in viral_content_list:
            viral_data.append({
                "platform": content.platform,
                "url": content.url,
                "title": content.title,
                "description": content.description,
                "author": content.author,
                "engagement_metrics": content.engagement_metrics,
                "screenshot_path": content.screenshot_path,
                "content_type": content.content_type,
                "hashtags": content.hashtags,
                "mentions": content.mentions,
                "timestamp": content.timestamp,
                "virality_score": content.virality_score
            })
        
        # Salva dados detalhados
        import json
        with open(os.path.join(save_dir, "viral_content_detailed.json"), 'w', encoding='utf-8') as f:
            json.dump(viral_data, f, ensure_ascii=False, indent=2)
        
        # Salva resumo
        with open(os.path.join(save_dir, "viral_summary.json"), 'w', encoding='utf-8') as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        
        logger.info(f"💾 Dados virais salvos em: {save_dir}")
        
    except Exception as e:
        logger.error(f"❌ Erro ao salvar dados virais: {e}")

# --- O resto do seu código (outras funções, se houver) permanece inalterado ---
