#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ARQV30 Enhanced - Google Authentication Manager
Sistema de gerenciamento de autenticação Google integrado ao ARQ300
"""

import os
import json
import logging
import asyncio
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Importações Google Auth
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import google.auth.exceptions

logger = logging.getLogger(__name__)

class GoogleAuthManager:
    """Gerenciador de autenticação Google para ARQ300"""
    
    def __init__(self):
        """Inicializa o gerenciador de autenticação"""
        # Carrega variáveis de ambiente
        load_dotenv()
        
        # Configurações OAuth
        self.SCOPES = [
            'https://www.googleapis.com/auth/cloud-platform',
            'https://www.googleapis.com/auth/drive.readonly',
            'https://www.googleapis.com/auth/youtube.readonly',
            'https://www.googleapis.com/auth/gmail.readonly',
            'https://www.googleapis.com/auth/analytics.readonly',
            'https://www.googleapis.com/auth/webmasters.readonly'
        ]
        
        # Caminhos dos arquivos
        self.credentials_file = os.getenv('GOOGLE_CREDENTIALS_FILE', 'credentials.json')
        self.token_file = os.getenv('GOOGLE_AUTH_TOKEN_PATH', 'token.json')
        
        # Estado interno
        self._credentials: Optional[Credentials] = None
        self._services: Dict[str, Any] = {}
        self._last_refresh: Optional[datetime] = None
        self._is_authenticated = False
        
        # Estatísticas
        self.stats = {
            'auth_attempts': 0,
            'successful_auths': 0,
            'token_refreshes': 0,
            'api_calls': 0,
            'last_auth_time': None,
            'last_error': None
        }
        
        logger.info("🔧 Google Auth Manager inicializado")
    
    @property
    def is_authenticated(self) -> bool:
        """Verifica se está autenticado"""
        return self._is_authenticated and self._credentials and self._credentials.valid
    
    @property
    def credentials(self) -> Optional[Credentials]:
        """Retorna credenciais atuais"""
        return self._credentials
    
    async def initialize(self) -> bool:
        """Inicializa o sistema de autenticação"""
        try:
            logger.info("🚀 Inicializando sistema de autenticação Google...")
            
            # Tenta carregar credenciais existentes
            if await self._load_existing_credentials():
                logger.info("✅ Credenciais existentes carregadas")
                return True
            
            logger.warning("⚠️ Nenhuma credencial válida encontrada")
            logger.info("💡 Execute 'python auth_setup.py' para configurar autenticação")
            return False
            
        except Exception as e:
            logger.error(f"❌ Erro na inicialização: {e}")
            self.stats['last_error'] = str(e)
            return False
    
    async def _load_existing_credentials(self) -> bool:
        """Carrega credenciais existentes"""
        try:
            if not Path(self.token_file).exists():
                return False
            
            self._credentials = Credentials.from_authorized_user_file(
                self.token_file, self.SCOPES
            )
            
            # Verifica se precisa renovar
            if self._credentials.expired and self._credentials.refresh_token:
                await self._refresh_credentials()
            
            if self._credentials.valid:
                self._is_authenticated = True
                self.stats['successful_auths'] += 1
                self.stats['last_auth_time'] = datetime.now().isoformat()
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"❌ Erro ao carregar credenciais: {e}")
            return False
    
    async def _refresh_credentials(self) -> bool:
        """Renova credenciais expiradas"""
        try:
            logger.info("🔄 Renovando credenciais...")
            
            self._credentials.refresh(Request())
            
            # Salva credenciais renovadas
            with open(self.token_file, 'w') as token:
                token.write(self._credentials.to_json())
            
            self._last_refresh = datetime.now()
            self.stats['token_refreshes'] += 1
            
            logger.info("✅ Credenciais renovadas com sucesso")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro ao renovar credenciais: {e}")
            self.stats['last_error'] = str(e)
            return False
    
    async def get_service(self, service_name: str, version: str = 'v3') -> Optional[Any]:
        """Obtém serviço Google API"""
        try:
            if not self.is_authenticated:
                logger.error("❌ Não autenticado - não é possível criar serviço")
                return None
            
            service_key = f"{service_name}_{version}"
            
            # Retorna serviço em cache se disponível
            if service_key in self._services:
                return self._services[service_key]
            
            # Cria novo serviço
            service = build(service_name, version, credentials=self._credentials)
            self._services[service_key] = service
            
            self.stats['api_calls'] += 1
            logger.debug(f"✅ Serviço {service_name} v{version} criado")
            
            return service
            
        except Exception as e:
            logger.error(f"❌ Erro ao criar serviço {service_name}: {e}")
            self.stats['last_error'] = str(e)
            return None
    
    async def test_authentication(self) -> Dict[str, Any]:
        """Testa autenticação com diferentes serviços"""
        results = {
            'authenticated': self.is_authenticated,
            'services_tested': {},
            'overall_status': 'unknown',
            'timestamp': datetime.now().isoformat()
        }
        
        if not self.is_authenticated:
            results['overall_status'] = 'not_authenticated'
            return results
        
        # Lista de serviços para testar
        services_to_test = [
            ('youtube', 'v3'),
            ('drive', 'v3'),
            ('gmail', 'v1'),
            ('analytics', 'v3')
        ]
        
        successful_tests = 0
        
        for service_name, version in services_to_test:
            try:
                service = await self.get_service(service_name, version)
                if service:
                    results['services_tested'][service_name] = {
                        'status': 'success',
                        'version': version
                    }
                    successful_tests += 1
                else:
                    results['services_tested'][service_name] = {
                        'status': 'failed',
                        'error': 'Service creation failed'
                    }
            except Exception as e:
                results['services_tested'][service_name] = {
                    'status': 'error',
                    'error': str(e)
                }
        
        # Determina status geral
        if successful_tests == len(services_to_test):
            results['overall_status'] = 'fully_functional'
        elif successful_tests > 0:
            results['overall_status'] = 'partially_functional'
        else:
            results['overall_status'] = 'not_functional'
        
        return results
    
    async def get_youtube_service(self):
        """Obtém serviço YouTube (método de conveniência)"""
        return await self.get_service('youtube', 'v3')
    
    async def get_drive_service(self):
        """Obtém serviço Google Drive (método de conveniência)"""
        return await self.get_service('drive', 'v3')
    
    async def get_gmail_service(self):
        """Obtém serviço Gmail (método de conveniência)"""
        return await self.get_service('gmail', 'v1')
    
    async def get_analytics_service(self):
        """Obtém serviço Google Analytics (método de conveniência)"""
        return await self.get_service('analytics', 'v3')
    
    def get_auth_status(self) -> Dict[str, Any]:
        """Retorna status detalhado da autenticação"""
        return {
            'is_authenticated': self.is_authenticated,
            'credentials_valid': self._credentials.valid if self._credentials else False,
            'credentials_expired': self._credentials.expired if self._credentials else True,
            'token_file_exists': Path(self.token_file).exists(),
            'credentials_file_exists': Path(self.credentials_file).exists(),
            'last_refresh': self._last_refresh.isoformat() if self._last_refresh else None,
            'scopes': self.SCOPES,
            'services_cached': list(self._services.keys()),
            'stats': self.stats.copy()
        }
    
    async def force_refresh(self) -> bool:
        """Força renovação das credenciais"""
        if not self._credentials:
            logger.error("❌ Nenhuma credencial para renovar")
            return False
        
        return await self._refresh_credentials()
    
    def clear_cache(self):
        """Limpa cache de serviços"""
        self._services.clear()
        logger.info("🧹 Cache de serviços limpo")
    
    async def revoke_credentials(self) -> bool:
        """Revoga credenciais atuais"""
        try:
            if self._credentials and self._credentials.token:
                # Revoga token no Google
                revoke_url = f"https://oauth2.googleapis.com/revoke?token={self._credentials.token}"
                import requests
                response = requests.post(revoke_url)
                
                if response.status_code == 200:
                    logger.info("✅ Credenciais revogadas no Google")
                else:
                    logger.warning(f"⚠️ Falha ao revogar no Google: {response.status_code}")
            
            # Remove arquivos locais
            if Path(self.token_file).exists():
                os.remove(self.token_file)
                logger.info(f"🗑️ Arquivo {self.token_file} removido")
            
            # Limpa estado interno
            self._credentials = None
            self._is_authenticated = False
            self.clear_cache()
            
            logger.info("✅ Credenciais revogadas com sucesso")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro ao revogar credenciais: {e}")
            return False

# Instância global do gerenciador
google_auth_manager = GoogleAuthManager()

async def initialize_google_auth() -> bool:
    """Inicializa autenticação Google (função de conveniência)"""
    return await google_auth_manager.initialize()

def get_google_auth_status() -> Dict[str, Any]:
    """Obtém status da autenticação Google (função de conveniência)"""
    return google_auth_manager.get_auth_status()

async def test_google_auth() -> Dict[str, Any]:
    """Testa autenticação Google (função de conveniência)"""
    return await google_auth_manager.test_authentication()