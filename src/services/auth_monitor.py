#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ARQV30 Enhanced - Monitor de Autenticação Google
Sistema de monitoramento contínuo da autenticação Google
"""

import os
import json
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

class AuthMonitor:
    """Monitor de autenticação Google"""
    
    def __init__(self, auth_manager):
        """Inicializa o monitor"""
        self.auth_manager = auth_manager
        self.monitoring_active = False
        self.check_interval = 300  # 5 minutos
        self.log_file = Path('auth_monitor.log')
        
        # Configuração de logging específico
        self.setup_logging()
        
        # Métricas de monitoramento
        self.metrics = {
            'total_checks': 0,
            'successful_checks': 0,
            'failed_checks': 0,
            'token_refreshes': 0,
            'service_failures': 0,
            'last_check': None,
            'uptime_start': datetime.now(),
            'alerts_sent': 0
        }
        
        # Histórico de eventos
        self.event_history: List[Dict[str, Any]] = []
        self.max_history_size = 1000
        
        logger.info("📊 Auth Monitor inicializado")
    
    def setup_logging(self):
        """Configura logging específico para monitoramento"""
        # Handler para arquivo de log do monitor
        monitor_handler = logging.FileHandler(self.log_file)
        monitor_handler.setLevel(logging.INFO)
        
        # Formato específico para monitoramento
        monitor_formatter = logging.Formatter(
            '%(asctime)s - AUTH_MONITOR - %(levelname)s - %(message)s'
        )
        monitor_handler.setFormatter(monitor_formatter)
        
        # Logger específico para monitoramento
        self.monitor_logger = logging.getLogger('auth_monitor')
        self.monitor_logger.addHandler(monitor_handler)
        self.monitor_logger.setLevel(logging.INFO)
    
    def log_event(self, event_type: str, message: str, level: str = 'INFO', **kwargs):
        """Registra evento de monitoramento"""
        timestamp = datetime.now()
        
        event = {
            'timestamp': timestamp.isoformat(),
            'type': event_type,
            'message': message,
            'level': level,
            **kwargs
        }
        
        # Adiciona ao histórico
        self.event_history.append(event)
        
        # Mantém tamanho do histórico
        if len(self.event_history) > self.max_history_size:
            self.event_history.pop(0)
        
        # Log no arquivo
        log_method = getattr(self.monitor_logger, level.lower(), self.monitor_logger.info)
        log_method(f"{event_type}: {message}")
    
    async def check_auth_health(self) -> Dict[str, Any]:
        """Verifica saúde da autenticação"""
        self.metrics['total_checks'] += 1
        
        try:
            # Verifica status básico
            status = self.auth_manager.get_auth_status()
            
            health_report = {
                'timestamp': datetime.now().isoformat(),
                'is_healthy': True,
                'issues': [],
                'warnings': [],
                'status': status
            }
            
            # Verifica se está autenticado
            if not status['is_authenticated']:
                health_report['is_healthy'] = False
                health_report['issues'].append('Not authenticated')
                self.log_event('AUTH_FAILURE', 'Sistema não autenticado', 'ERROR')
            
            # Verifica se credenciais estão válidas
            if not status['credentials_valid']:
                health_report['is_healthy'] = False
                health_report['issues'].append('Invalid credentials')
                self.log_event('CREDENTIAL_INVALID', 'Credenciais inválidas', 'ERROR')
            
            # Verifica se credenciais estão expiradas
            if status['credentials_expired']:
                health_report['warnings'].append('Credentials expired')
                self.log_event('CREDENTIAL_EXPIRED', 'Credenciais expiradas', 'WARNING')
                
                # Tenta renovar automaticamente
                if self.auth_manager._credentials and self.auth_manager._credentials.refresh_token:
                    try:
                        await self.auth_manager.force_refresh()
                        self.metrics['token_refreshes'] += 1
                        self.log_event('TOKEN_REFRESH', 'Token renovado automaticamente', 'INFO')
                    except Exception as e:
                        health_report['issues'].append(f'Failed to refresh token: {e}')
                        self.log_event('REFRESH_FAILURE', f'Falha na renovação: {e}', 'ERROR')
            
            # Verifica arquivos necessários
            if not status['token_file_exists']:
                health_report['issues'].append('Token file missing')
                self.log_event('FILE_MISSING', 'Arquivo token.json não encontrado', 'ERROR')
            
            if not status['credentials_file_exists']:
                health_report['issues'].append('Credentials file missing')
                self.log_event('FILE_MISSING', 'Arquivo credentials.json não encontrado', 'ERROR')
            
            # Testa serviços se autenticado
            if status['is_authenticated']:
                service_test = await self.auth_manager.test_authentication()
                
                if service_test['overall_status'] == 'not_functional':
                    health_report['is_healthy'] = False
                    health_report['issues'].append('No services functional')
                    self.metrics['service_failures'] += 1
                    self.log_event('SERVICE_FAILURE', 'Nenhum serviço funcionando', 'ERROR')
                elif service_test['overall_status'] == 'partially_functional':
                    health_report['warnings'].append('Some services not functional')
                    self.log_event('SERVICE_PARTIAL', 'Alguns serviços não funcionando', 'WARNING')
            
            # Atualiza métricas
            if health_report['is_healthy']:
                self.metrics['successful_checks'] += 1
            else:
                self.metrics['failed_checks'] += 1
            
            self.metrics['last_check'] = datetime.now().isoformat()
            
            return health_report
            
        except Exception as e:
            self.metrics['failed_checks'] += 1
            self.log_event('MONITOR_ERROR', f'Erro no monitoramento: {e}', 'ERROR')
            
            return {
                'timestamp': datetime.now().isoformat(),
                'is_healthy': False,
                'issues': [f'Monitor error: {e}'],
                'warnings': [],
                'status': {}
            }
    
    async def start_monitoring(self):
        """Inicia monitoramento contínuo"""
        if self.monitoring_active:
            logger.warning("⚠️ Monitoramento já está ativo")
            return
        
        self.monitoring_active = True
        self.metrics['uptime_start'] = datetime.now()
        
        self.log_event('MONITOR_START', 'Monitoramento iniciado', 'INFO')
        logger.info("🚀 Monitoramento de autenticação iniciado")
        
        try:
            while self.monitoring_active:
                # Executa verificação de saúde
                health_report = await self.check_auth_health()
                
                # Log resumido
                if health_report['is_healthy']:
                    logger.debug("✅ Verificação de saúde: OK")
                else:
                    logger.warning(f"⚠️ Problemas detectados: {len(health_report['issues'])} issues, {len(health_report['warnings'])} warnings")
                
                # Aguarda próxima verificação
                await asyncio.sleep(self.check_interval)
                
        except asyncio.CancelledError:
            logger.info("🛑 Monitoramento cancelado")
        except Exception as e:
            logger.error(f"❌ Erro no loop de monitoramento: {e}")
        finally:
            self.monitoring_active = False
            self.log_event('MONITOR_STOP', 'Monitoramento parado', 'INFO')
    
    def stop_monitoring(self):
        """Para monitoramento"""
        if self.monitoring_active:
            self.monitoring_active = False
            logger.info("🛑 Parando monitoramento...")
    
    def get_metrics(self) -> Dict[str, Any]:
        """Retorna métricas de monitoramento"""
        uptime = datetime.now() - self.metrics['uptime_start']
        
        return {
            **self.metrics,
            'uptime_seconds': uptime.total_seconds(),
            'uptime_formatted': str(uptime),
            'success_rate': (
                self.metrics['successful_checks'] / max(self.metrics['total_checks'], 1) * 100
            ),
            'monitoring_active': self.monitoring_active
        }
    
    def get_recent_events(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Retorna eventos recentes"""
        return self.event_history[-limit:] if self.event_history else []
    
    def get_events_by_type(self, event_type: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Retorna eventos por tipo"""
        filtered_events = [
            event for event in self.event_history 
            if event['type'] == event_type
        ]
        return filtered_events[-limit:] if filtered_events else []
    
    def clear_history(self):
        """Limpa histórico de eventos"""
        self.event_history.clear()
        self.log_event('HISTORY_CLEAR', 'Histórico de eventos limpo', 'INFO')
    
    def export_logs(self, output_file: str = None) -> str:
        """Exporta logs para arquivo"""
        if not output_file:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_file = f'auth_monitor_export_{timestamp}.json'
        
        export_data = {
            'export_timestamp': datetime.now().isoformat(),
            'metrics': self.get_metrics(),
            'events': self.event_history
        }
        
        with open(output_file, 'w') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
        
        self.log_event('LOG_EXPORT', f'Logs exportados para {output_file}', 'INFO')
        return output_file
    
    async def send_alert(self, message: str, level: str = 'WARNING'):
        """Envia alerta (placeholder para integração futura)"""
        self.metrics['alerts_sent'] += 1
        self.log_event('ALERT_SENT', message, level)
        
        # Aqui poderia integrar com:
        # - Email
        # - Slack
        # - Discord
        # - SMS
        # - Webhook
        
        logger.warning(f"🚨 ALERTA: {message}")

# Função para criar monitor
def create_auth_monitor(auth_manager) -> AuthMonitor:
    """Cria instância do monitor de autenticação"""
    return AuthMonitor(auth_manager)