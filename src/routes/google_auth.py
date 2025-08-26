#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ARQV30 Enhanced - Rotas de Autenticação Google
Endpoints para gerenciar autenticação Google OAuth 2.0
"""

import os
import json
import logging
import asyncio
from datetime import datetime
from flask import Blueprint, request, jsonify, redirect, url_for, session
from typing import Dict, Any

# Importações do sistema
try:
    from services.google_auth_manager import google_auth_manager, get_google_auth_status, test_google_auth
    from services.auth_monitor import create_auth_monitor
    HAS_GOOGLE_AUTH = True
except ImportError:
    HAS_GOOGLE_AUTH = False

logger = logging.getLogger(__name__)

# Blueprint para rotas de autenticação
google_auth_bp = Blueprint('google_auth', __name__, url_prefix='/auth/google')

# Monitor de autenticação (inicializado quando necessário)
auth_monitor = None

def get_auth_monitor():
    """Obtém instância do monitor de autenticação"""
    global auth_monitor
    if auth_monitor is None and HAS_GOOGLE_AUTH:
        auth_monitor = create_auth_monitor(google_auth_manager)
    return auth_monitor

@google_auth_bp.route('/status', methods=['GET'])
def auth_status():
    """Retorna status da autenticação Google"""
    try:
        if not HAS_GOOGLE_AUTH:
            return jsonify({
                'success': False,
                'error': 'Google Auth não disponível',
                'available': False
            }), 503
        
        status = get_google_auth_status()
        
        return jsonify({
            'success': True,
            'status': status,
            'available': True,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"❌ Erro ao obter status: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'available': HAS_GOOGLE_AUTH
        }), 500

@google_auth_bp.route('/test', methods=['POST'])
def test_auth():
    """Testa autenticação Google"""
    try:
        if not HAS_GOOGLE_AUTH:
            return jsonify({
                'success': False,
                'error': 'Google Auth não disponível'
            }), 503
        
        # Executa teste assíncrono
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            test_results = loop.run_until_complete(test_google_auth())
        finally:
            loop.close()
        
        return jsonify({
            'success': True,
            'test_results': test_results,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"❌ Erro no teste de autenticação: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@google_auth_bp.route('/initialize', methods=['POST'])
def initialize_auth():
    """Inicializa autenticação Google"""
    try:
        if not HAS_GOOGLE_AUTH:
            return jsonify({
                'success': False,
                'error': 'Google Auth não disponível'
            }), 503
        
        # Executa inicialização assíncrona
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            success = loop.run_until_complete(google_auth_manager.initialize())
        finally:
            loop.close()
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Autenticação inicializada com sucesso',
                'status': get_google_auth_status(),
                'timestamp': datetime.now().isoformat()
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Falha na inicialização',
                'message': 'Execute auth_setup.py para configurar autenticação'
            }), 400
        
    except Exception as e:
        logger.error(f"❌ Erro na inicialização: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@google_auth_bp.route('/refresh', methods=['POST'])
def refresh_token():
    """Força renovação do token"""
    try:
        if not HAS_GOOGLE_AUTH:
            return jsonify({
                'success': False,
                'error': 'Google Auth não disponível'
            }), 503
        
        if not google_auth_manager.is_authenticated:
            return jsonify({
                'success': False,
                'error': 'Não autenticado'
            }), 401
        
        # Executa renovação assíncrona
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            success = loop.run_until_complete(google_auth_manager.force_refresh())
        finally:
            loop.close()
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Token renovado com sucesso',
                'status': get_google_auth_status(),
                'timestamp': datetime.now().isoformat()
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Falha na renovação do token'
            }), 400
        
    except Exception as e:
        logger.error(f"❌ Erro na renovação: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@google_auth_bp.route('/revoke', methods=['POST'])
def revoke_auth():
    """Revoga autenticação atual"""
    try:
        if not HAS_GOOGLE_AUTH:
            return jsonify({
                'success': False,
                'error': 'Google Auth não disponível'
            }), 503
        
        # Executa revogação assíncrona
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            success = loop.run_until_complete(google_auth_manager.revoke_credentials())
        finally:
            loop.close()
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Autenticação revogada com sucesso',
                'timestamp': datetime.now().isoformat()
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Falha na revogação'
            }), 400
        
    except Exception as e:
        logger.error(f"❌ Erro na revogação: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@google_auth_bp.route('/services', methods=['GET'])
def list_services():
    """Lista serviços Google disponíveis"""
    try:
        if not HAS_GOOGLE_AUTH:
            return jsonify({
                'success': False,
                'error': 'Google Auth não disponível'
            }), 503
        
        if not google_auth_manager.is_authenticated:
            return jsonify({
                'success': False,
                'error': 'Não autenticado',
                'services': []
            }), 401
        
        # Lista de serviços suportados
        supported_services = [
            {
                'name': 'YouTube',
                'service_name': 'youtube',
                'version': 'v3',
                'description': 'YouTube Data API'
            },
            {
                'name': 'Google Drive',
                'service_name': 'drive',
                'version': 'v3',
                'description': 'Google Drive API'
            },
            {
                'name': 'Gmail',
                'service_name': 'gmail',
                'version': 'v1',
                'description': 'Gmail API'
            },
            {
                'name': 'Google Analytics',
                'service_name': 'analytics',
                'version': 'v3',
                'description': 'Google Analytics API'
            }
        ]
        
        return jsonify({
            'success': True,
            'services': supported_services,
            'authenticated': google_auth_manager.is_authenticated,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"❌ Erro ao listar serviços: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@google_auth_bp.route('/monitor/start', methods=['POST'])
def start_monitoring():
    """Inicia monitoramento de autenticação"""
    try:
        if not HAS_GOOGLE_AUTH:
            return jsonify({
                'success': False,
                'error': 'Google Auth não disponível'
            }), 503
        
        monitor = get_auth_monitor()
        if not monitor:
            return jsonify({
                'success': False,
                'error': 'Monitor não disponível'
            }), 503
        
        if monitor.monitoring_active:
            return jsonify({
                'success': False,
                'error': 'Monitoramento já está ativo'
            }), 400
        
        # Inicia monitoramento em background
        import threading
        
        def run_monitor():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(monitor.start_monitoring())
            finally:
                loop.close()
        
        monitor_thread = threading.Thread(target=run_monitor, daemon=True)
        monitor_thread.start()
        
        return jsonify({
            'success': True,
            'message': 'Monitoramento iniciado',
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"❌ Erro ao iniciar monitoramento: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@google_auth_bp.route('/monitor/stop', methods=['POST'])
def stop_monitoring():
    """Para monitoramento de autenticação"""
    try:
        if not HAS_GOOGLE_AUTH:
            return jsonify({
                'success': False,
                'error': 'Google Auth não disponível'
            }), 503
        
        monitor = get_auth_monitor()
        if not monitor:
            return jsonify({
                'success': False,
                'error': 'Monitor não disponível'
            }), 503
        
        monitor.stop_monitoring()
        
        return jsonify({
            'success': True,
            'message': 'Monitoramento parado',
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"❌ Erro ao parar monitoramento: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@google_auth_bp.route('/monitor/metrics', methods=['GET'])
def get_monitor_metrics():
    """Obtém métricas do monitor"""
    try:
        if not HAS_GOOGLE_AUTH:
            return jsonify({
                'success': False,
                'error': 'Google Auth não disponível'
            }), 503
        
        monitor = get_auth_monitor()
        if not monitor:
            return jsonify({
                'success': False,
                'error': 'Monitor não disponível'
            }), 503
        
        metrics = monitor.get_metrics()
        
        return jsonify({
            'success': True,
            'metrics': metrics,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"❌ Erro ao obter métricas: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@google_auth_bp.route('/monitor/events', methods=['GET'])
def get_monitor_events():
    """Obtém eventos do monitor"""
    try:
        if not HAS_GOOGLE_AUTH:
            return jsonify({
                'success': False,
                'error': 'Google Auth não disponível'
            }), 503
        
        monitor = get_auth_monitor()
        if not monitor:
            return jsonify({
                'success': False,
                'error': 'Monitor não disponível'
            }), 503
        
        # Parâmetros opcionais
        limit = request.args.get('limit', 50, type=int)
        event_type = request.args.get('type')
        
        if event_type:
            events = monitor.get_events_by_type(event_type, limit)
        else:
            events = monitor.get_recent_events(limit)
        
        return jsonify({
            'success': True,
            'events': events,
            'count': len(events),
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"❌ Erro ao obter eventos: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# Função para registrar blueprint
def register_google_auth_routes(app):
    """Registra rotas de autenticação Google"""
    app.register_blueprint(google_auth_bp)
    logger.info("✅ Rotas de autenticação Google registradas")

# Informações sobre disponibilidade
def get_auth_info():
    """Retorna informações sobre disponibilidade da autenticação"""
    return {
        'available': HAS_GOOGLE_AUTH,
        'routes_registered': True,
        'endpoints': [
            '/auth/google/status',
            '/auth/google/test',
            '/auth/google/initialize',
            '/auth/google/refresh',
            '/auth/google/revoke',
            '/auth/google/services',
            '/auth/google/monitor/start',
            '/auth/google/monitor/stop',
            '/auth/google/monitor/metrics',
            '/auth/google/monitor/events'
        ]
    }