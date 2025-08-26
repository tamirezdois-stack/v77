
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ARQV30 Enhanced v3.0 - AI Manager com Sistema de Ferramentas
Gerenciador inteligente de múltiplas IAs com suporte a ferramentas e fallback automático
"""

import os
import logging
import time
import json
from typing import Dict, List, Optional, Any, Union
import requests
from datetime import datetime, timedelta

# Imports condicionais para os clientes de IA
try:
    import google.generativeai as genai
    HAS_GEMINI = True
except ImportError:
    HAS_GEMINI = False

try:
    import openai
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False

try:
    from services.groq_client import groq_client
    HAS_GROQ_CLIENT = True
except ImportError:
    HAS_GROQ_CLIENT = False

try:
    from services.search_api_manager import search_api_manager
    HAS_SEARCH_MANAGER = True
except ImportError:
    HAS_SEARCH_MANAGER = False

try:
    from services.google_auth_manager import google_auth_manager
    HAS_GOOGLE_AUTH = True
except ImportError:
    HAS_GOOGLE_AUTH = False

logger = logging.getLogger(__name__)

class AIManager:
    """Gerenciador de IA com fallback automático e suporte a ferramentas"""

    def __init__(self):
        """Inicializa o gerenciador de IA"""
        self.providers = {}
        self.last_used_provider = None
        self.error_counts = {}
        self.performance_metrics = {}
        self.circuit_breaker = {}
        
        # Verifica configuração de ambiente
        self._check_environment_config()
        
        self._initialize_providers()
        logger.info(f"✅ AI Manager inicializado com {len(self.providers)} provedores")

    def _check_environment_config(self):
        """Verifica e reporta configuração de ambiente"""
        logger.info("🔧 Verificando configuração de ambiente...")
        
        # Verifica chaves de API (ORDEM DE PRIORIDADE)
        api_keys = {
            'OPENROUTER_API_KEY': os.getenv('OPENROUTER_API_KEY') or os.getenv('OPENROUTER_API_KEY_2'),  # IA PRIMÁRIA
            'GEMINI_API_KEY': os.getenv('GEMINI_API_KEY'),  # FALLBACK SECUNDÁRIO
            'OPENAI_API_KEY': os.getenv('OPENAI_API_KEY'),  # FALLBACK TERCIÁRIO
            'GROQ_API_KEY': os.getenv('GROQ_API_KEY')
        }
        
        # Verifica autenticação Google
        google_auth_keys = {
            'GOOGLE_CLIENT_ID': os.getenv('GOOGLE_CLIENT_ID'),
            'GOOGLE_CLIENT_SECRET': os.getenv('GOOGLE_CLIENT_SECRET'),
            'GOOGLE_PROJECT_ID': os.getenv('GOOGLE_PROJECT_ID')
        }
        
        configured_keys = []
        missing_keys = []
        
        for key_name, key_value in api_keys.items():
            if key_value:
                configured_keys.append(key_name)
                logger.info(f"   ✅ {key_name}: configurada")
            else:
                missing_keys.append(key_name)
                logger.warning(f"   ❌ {key_name}: não configurada")
        
        if not configured_keys:
            logger.error("❌ NENHUMA CHAVE DE API CONFIGURADA!")
            logger.error("❌ Configure pelo menos uma das seguintes variáveis de ambiente:")
            for key in missing_keys:
                logger.error(f"   - {key}")
        else:
            logger.info(f"✅ {len(configured_keys)} chaves de API configuradas")
        
        # Verifica configuração Google Auth
        google_configured = []
        google_missing = []
        
        for key_name, key_value in google_auth_keys.items():
            if key_value:
                google_configured.append(key_name)
                logger.info(f"   ✅ {key_name}: configurada")
            else:
                google_missing.append(key_name)
                logger.warning(f"   ⚠️ {key_name}: não configurada")
        
        if len(google_configured) == len(google_auth_keys):
            logger.info("✅ Autenticação Google completamente configurada")
            # Inicializa autenticação Google se disponível
            if HAS_GOOGLE_AUTH:
                try:
                    import asyncio
                    # Tenta inicializar em background (não bloqueia)
                    asyncio.create_task(google_auth_manager.initialize())
                    logger.info("🔐 Inicialização Google Auth agendada")
                except Exception as e:
                    logger.warning(f"⚠️ Erro ao agendar inicialização Google Auth: {e}")
        else:
            logger.warning(f"⚠️ Autenticação Google parcialmente configurada ({len(google_configured)}/{len(google_auth_keys)})")

    def _initialize_providers(self):
        """Inicializa todos os provedores de IA disponíveis"""
        
        # 🥇 PRIORIDADE 1: OpenRouter (IA PRIMÁRIA)
        try:
            openrouter_key = os.getenv('OPENROUTER_API_KEY') or os.getenv('OPENROUTER_API_KEY_2')
            if openrouter_key and HAS_OPENAI:
                # Usa cliente OpenAI com endpoint OpenRouter
                openai_client = openai.OpenAI(
                    api_key=openrouter_key,
                    base_url="https://openrouter.ai/api/v1"
                )
                self.providers['openrouter'] = {
                    'client': openai_client,
                    'available': True,
                    'model': 'qwen/qwen2.5-vl-32b-instruct:free',
                    'priority': 1,
                    'error_count': 0,
                    'consecutive_failures': 0,
                    'max_errors': 3,
                    'last_success': None,
                    'supports_tools': True,
                    'type': 'openrouter'
                }
                logger.info("🥇 OpenRouter (Qwen 2.5 VL) inicializado como IA PRIMÁRIA")
            else:
                logger.warning("⚠️ OPENROUTER_API_KEY não configurada - IA PRIMÁRIA indisponível!")
        except Exception as e:
            logger.error(f"❌ Erro ao inicializar OpenRouter: {e}")

        # 🥈 PRIORIDADE 2: Gemini (FALLBACK SECUNDÁRIO)
        try:
            if HAS_GEMINI:
                api_key = os.getenv('GEMINI_API_KEY')
                if api_key:
                    genai.configure(api_key=api_key)
                    self.providers['gemini'] = {
                        'client': genai,
                        'available': True,
                        'model': 'gemini-2.0-flash-exp',
                        'priority': 2,
                        'error_count': 0,
                        'consecutive_failures': 0,
                        'max_errors': 5,
                        'last_success': None,
                        'supports_tools': True,
                        'type': 'gemini'
                    }
                    logger.info("🥈 Gemini 2.0 Flash inicializado como FALLBACK SECUNDÁRIO")
                else:
                    logger.warning("⚠️ GEMINI_API_KEY não configurada - Fallback indisponível!")
            else:
                logger.warning("⚠️ Biblioteca 'google-generativeai' não instalada.")
        except Exception as e:
            logger.warning(f"⚠️ Gemini não disponível: {str(e)}")

        # 🥉 PRIORIDADE 3: OpenAI (FALLBACK TERCIÁRIO)
        try:
            if HAS_OPENAI:
                api_key = os.getenv('OPENAI_API_KEY')
                if api_key:
                    openai_client = openai.OpenAI(api_key=api_key)
                    self.providers['openai'] = {
                        'client': openai_client,
                        'available': True,
                        'model': 'gpt-4-0125-preview',
                        'priority': 3,
                        'error_count': 0,
                        'consecutive_failures': 0,
                        'max_errors': 3,
                        'last_success': None,
                        'supports_tools': True,
                        'type': 'openai'
                    }
                    logger.info("🥉 OpenAI GPT-4 inicializado como FALLBACK TERCIÁRIO")
                else:
                    logger.info("ℹ️ OPENAI_API_KEY não configurada.")
            else:
                logger.info("ℹ️ Biblioteca 'openai' não instalada.")
        except Exception as e:
            logger.warning(f"ℹ️ OpenAI não disponível: {str(e)}")

        # Inicializa Groq
        try:
            if HAS_GROQ_CLIENT and groq_client and groq_client.is_enabled():
                self.providers['groq'] = {
                    'client': groq_client,
                    'available': True,
                    'model': 'llama3-70b-8192',
                    'priority': 3,
                    'error_count': 0,
                    'consecutive_failures': 0,
                    'max_errors': 3,
                    'last_success': None,
                    'supports_tools': False
                }
                logger.info("✅ Groq (llama3-70b-8192) inicializado.")
            else:
                logger.info("ℹ️ Groq não disponível ou não configurado.")
        except Exception as e:
            logger.warning(f"ℹ️ Groq não disponível: {str(e)}")

    def _get_available_provider(self, require_tools: bool = False) -> Optional[str]:
        """Seleciona o melhor provedor disponível"""
        available_providers = []
        
        logger.debug(f"🔍 Verificando provedores disponíveis (require_tools={require_tools})")
        
        for name, provider in self.providers.items():
            logger.debug(f"   {name}: available={provider['available']}, consecutive_failures={provider['consecutive_failures']}/{provider['max_errors']}")
            
            if not provider['available']:
                logger.debug(f"   ❌ {name}: não disponível")
                continue
                
            if require_tools and not provider.get('supports_tools', False):
                logger.debug(f"   ❌ {name}: não suporta ferramentas")
                continue
                
            if provider['consecutive_failures'] >= provider['max_errors']:
                logger.debug(f"   ❌ {name}: muitas falhas consecutivas")
                continue
                
            logger.debug(f"   ✅ {name}: disponível (prioridade {provider['priority']})")
            available_providers.append((name, provider['priority']))
        
        if not available_providers:
            logger.error("❌ NENHUM PROVEDOR DE IA DISPONÍVEL!")
            logger.error(f"❌ Total de provedores configurados: {len(self.providers)}")
            for name, provider in self.providers.items():
                logger.error(f"   {name}: available={provider['available']}, failures={provider['consecutive_failures']}")
            
            # CORREÇÃO: Tenta reinicializar provedores se nenhum disponível
            logger.warning("⚠️ Tentando reinicializar provedores...")
            self._initialize_providers()
            
            # Verifica novamente após reinicialização
            available_providers = []
            for name, provider in self.providers.items():
                if not provider['available']:
                    continue
                if provider['consecutive_failures'] >= provider['max_errors']:
                    # CORREÇÃO: Reset de falhas consecutivas para dar nova chance
                    logger.warning(f"⚠️ Resetando falhas consecutivas para {name}")
                    provider['consecutive_failures'] = 0
                
                logger.debug(f"   ✅ {name}: disponível após reset (prioridade {provider['priority']})")
                available_providers.append((name, provider['priority']))
            
            if not available_providers:
                logger.error("❌ AINDA NENHUM PROVEDOR DISPONÍVEL APÓS REINICIALIZAÇÃO!")
                return None
            
        # Ordena por prioridade (menor número = maior prioridade)
        available_providers.sort(key=lambda x: x[1])
        selected = available_providers[0][0]
        logger.info(f"✅ Provedor selecionado: {selected}")
        return selected

    async def google_search_tool(self, query: str) -> Dict[str, Any]:
        """Ferramenta de busca Google para uso pela IA"""
        try:
            if not HAS_SEARCH_MANAGER:
                return {'error': 'Search manager não disponível'}
            
            logger.info(f"🔍 IA solicitou busca: {query}")
            results = await search_api_manager.interleaved_search(query)
            
            # Formata resultados para a IA
            formatted_results = []
            for result in results.get('all_results', []):
                if result.get('success') and result.get('results'):
                    for item in result['results'][:5]:  # Limita a 5 resultados por provedor
                        if isinstance(item, dict):
                            formatted_item = {
                                'title': item.get('title', ''),
                                'url': item.get('url') or item.get('link', ''),
                                'snippet': item.get('snippet') or item.get('content', '')[:200]
                            }
                            if formatted_item['url']:
                                formatted_results.append(formatted_item)
            
            return {
                'query': query,
                'results': formatted_results[:10],  # Máximo 10 resultados
                'total_found': len(formatted_results)
            }
            
        except Exception as e:
            logger.error(f"❌ Erro na busca: {e}")
            return {'error': f'Erro na busca: {str(e)}'}

    def _get_google_search_function_definition(self) -> Dict[str, Any]:
        """Definição da função de busca Google para Gemini"""
        return {
            "name": "google_search",
            "description": "Busca informações atualizadas na internet usando múltiplos provedores de busca",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Termo de busca para encontrar informações relevantes"
                    }
                },
                "required": ["query"]
            }
        }

    async def generate_with_tools(self, prompt: str, context: str = "", tools: List[str] = None, max_iterations: int = 5) -> str:
        """
        Gera texto com suporte a ferramentas (function calling)
        
        Args:
            prompt: Prompt principal para a IA
            context: Contexto adicional (dados coletados)
            tools: Lista de ferramentas disponíveis ['google_search']
            max_iterations: Máximo de iterações para evitar loops
        """
        if tools is None:
            tools = ['google_search']
        
        # Verifica se há provedores com suporte a ferramentas
        provider_name = self._get_available_provider(require_tools=True)
        if not provider_name:
            logger.warning("⚠️ Nenhum provedor com suporte a ferramentas disponível, usando geração normal")
            return await self.generate_text(prompt + "\n\n" + context)
        
        provider = self.providers[provider_name]
        logger.info(f"🤖 Usando {provider_name} com ferramentas: {tools}")
        
        # Prepara mensagens
        full_prompt = f"{prompt}\n\nContexto disponível:\n{context}"
        
        # Loop de execução com ferramentas
        iteration = 0
        conversation_history = []
        
        while iteration < max_iterations:
            iteration += 1
            logger.info(f"🔄 Iteração {iteration}/{max_iterations}")
            
            try:
                if provider_name == 'gemini':
                    result = await self._execute_gemini_with_tools(full_prompt, tools, conversation_history)
                elif provider_name == 'openai':
                    result = await self._execute_openai_with_tools(full_prompt, tools, conversation_history)
                else:
                    # Fallback para geração normal
                    return await self.generate_text(full_prompt)
                
                if result['type'] == 'text':
                    logger.info(f"✅ Resposta final gerada em {iteration} iterações")
                    return result['content']
                elif result['type'] == 'tool_call':
                    # Executa a ferramenta solicitada
                    tool_name = result['tool_name']
                    tool_args = result['tool_args']
                    
                    if tool_name == 'google_search' and 'query' in tool_args:
                        search_result = await self.google_search_tool(tool_args['query'])
                        conversation_history.append({
                            'type': 'tool_call',
                            'tool_name': tool_name,
                            'args': tool_args,
                            'result': search_result
                        })
                        
                        # Atualiza o contexto com os resultados da busca
                        search_context = self._format_search_results(search_result)
                        full_prompt += f"\n\nResultados da busca para '{tool_args['query']}':\n{search_context}"
                    else:
                        logger.warning(f"⚠️ Ferramenta {tool_name} não reconhecida ou argumentos inválidos")
                        break
                
            except Exception as e:
                logger.error(f"❌ Erro na iteração {iteration}: {e}")
                break
        
        logger.warning(f"⚠️ Máximo de iterações atingido ({max_iterations}), retornando resposta parcial")
        return "Análise realizada com ferramentas, mas processo interrompido por limite de iterações."

    async def _execute_gemini_with_tools(self, prompt: str, tools: List[str], history: List[Dict]) -> Dict[str, Any]:
        """Executa Gemini com suporte a ferramentas"""
        try:
            model = genai.GenerativeModel('gemini-2.0-flash-exp')
            
            # CORREÇÃO: Sanitiza prompt para evitar erros de 'object'
            if not isinstance(prompt, str):
                prompt = str(prompt)
            
            # Prepara function declarations se google_search está nas tools
            function_declarations = []
            if 'google_search' in tools:
                try:
                    function_declarations.append(self._get_google_search_function_definition())
                except Exception as func_error:
                    logger.warning(f"⚠️ Erro ao preparar function declaration: {func_error}")
                    # Fallback: usa geração sem ferramentas
                    response = model.generate_content(prompt)
                    return {
                        'type': 'text',
                        'content': response.text
                    }
            
            # Configura ferramentas se disponíveis
            tool_config = None
            if function_declarations:
                try:
                    tool_config = genai.protos.Tool(function_declarations=function_declarations)
                except Exception as tool_error:
                    logger.warning(f"⚠️ Erro ao configurar ferramentas: {tool_error}")
                    # Fallback: usa geração sem ferramentas
                    response = model.generate_content(prompt)
                    return {
                        'type': 'text',
                        'content': response.text
                    }
            
            # Inicia chat com ferramentas
            try:
                if tool_config:
                    chat = model.start_chat(tools=[tool_config])
                else:
                    chat = model.start_chat()
                
                # Envia mensagem
                response = chat.send_message(prompt)
                
            except Exception as chat_error:
                logger.warning(f"⚠️ Erro no chat com ferramentas: {chat_error}")
                # Fallback: usa geração direta
                response = model.generate_content(prompt)
                return {
                    'type': 'text',
                    'content': response.text
                }
            
            # Verifica se há function calls
            try:
                if response.candidates and response.candidates[0].content.parts:
                    for part in response.candidates[0].content.parts:
                        if hasattr(part, 'function_call') and part.function_call:
                            function_call = part.function_call
                            return {
                                'type': 'tool_call',
                                'tool_name': function_call.name,
                                'tool_args': dict(function_call.args)
                            }
            except Exception as parse_error:
                logger.warning(f"⚠️ Erro ao processar function calls: {parse_error}")
            
            # Se não há function calls, retorna o texto
            return {
                'type': 'text',
                'content': response.text if hasattr(response, 'text') else str(response)
            }
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"❌ Erro no Gemini com ferramentas: {error_msg}")
            
            # CORREÇÃO: Se erro contém 'object', tenta fallback
            if "object" in error_msg.lower():
                logger.warning("⚠️ Erro 'object' detectado, tentando fallback sem ferramentas")
                try:
                    model = genai.GenerativeModel('gemini-2.0-flash-exp')
                    response = model.generate_content(str(prompt))
                    return {
                        'type': 'text',
                        'content': response.text
                    }
                except Exception as fallback_error:
                    logger.error(f"❌ Fallback também falhou: {fallback_error}")
            
            raise

    async def _execute_openai_with_tools(self, prompt: str, tools: List[str], history: List[Dict]) -> Dict[str, Any]:
        """Executa OpenAI com suporte a ferramentas"""
        try:
            # Prepara tools para OpenAI
            openai_tools = []
            if 'google_search' in tools:
                openai_tools.append({
                    "type": "function",
                    "function": self._get_google_search_function_definition()
                })
            
            messages = [{"role": "user", "content": prompt}]
            
            # Adiciona histórico se existir
            for item in history:
                if item['type'] == 'tool_call':
                    messages.append({
                        "role": "assistant",
                        "tool_calls": [{
                            "id": f"call_{int(time.time())}",
                            "type": "function",
                            "function": {
                                "name": item['tool_name'],
                                "arguments": json.dumps(item['args'])
                            }
                        }]
                    })
                    messages.append({
                        "role": "tool",
                        "tool_call_id": f"call_{int(time.time())}",
                        "content": json.dumps(item['result'])
                    })
            
            # Faz a chamada
            if openai_tools:
                response = openai.ChatCompletion.create(
                    model="gpt-4-0125-preview",
                    messages=messages,
                    tools=openai_tools,
                    tool_choice="auto"
                )
            else:
                response = openai.ChatCompletion.create(
                    model="gpt-4-0125-preview",
                    messages=messages
                )
            
            message = response.choices[0].message
            
            # Verifica tool calls
            if hasattr(message, 'tool_calls') and message.tool_calls:
                tool_call = message.tool_calls[0]
                return {
                    'type': 'tool_call',
                    'tool_name': tool_call.function.name,
                    'tool_args': json.loads(tool_call.function.arguments)
                }
            
            return {
                'type': 'text',
                'content': message.content
            }
            
        except Exception as e:
            logger.error(f"❌ Erro no OpenAI com ferramentas: {e}")
            raise

    def _format_search_results(self, search_result: Dict[str, Any]) -> str:
        """Formata resultados de busca para contexto da IA"""
        if 'error' in search_result:
            return f"Erro na busca: {search_result['error']}"
        
        formatted = f"Busca: {search_result.get('query', '')}\n"
        formatted += f"Total encontrado: {search_result.get('total_found', 0)} resultados\n\n"
        
        for i, result in enumerate(search_result.get('results', []), 1):
            formatted += f"{i}. {result.get('title', 'Sem título')}\n"
            formatted += f"   URL: {result.get('url', '')}\n"
            formatted += f"   Resumo: {result.get('snippet', 'Sem descrição')}\n\n"
        
        return formatted

    async def generate_text(self, prompt: str, max_tokens: int = 8192, temperature: float = 0.7) -> str:
        """Gera texto usando o melhor provedor disponível com retry robusto"""
        
        # CORREÇÃO: Sanitiza prompt para evitar erros de 'object'
        if not isinstance(prompt, str):
            prompt = str(prompt)
        
        max_retries = 3
        last_error = None
        
        for attempt in range(max_retries):
            provider_name = self._get_available_provider()
            
            if not provider_name:
                # Tenta reinicializar provedores antes de falhar
                logger.warning(f"⚠️ Nenhum provedor disponível na tentativa {attempt + 1} - tentando reinicializar...")
                self._initialize_providers()
                provider_name = self._get_available_provider()
                
                if not provider_name:
                    if attempt == max_retries - 1:
                        logger.error("❌ FALHA CRÍTICA: Nenhum provedor de IA disponível após múltiplas tentativas")
                        logger.error("❌ Verifique se as chaves de API estão configuradas:")
                        logger.error("   - OPENROUTER_API_KEY (IA PRIMÁRIA)")
                        logger.error("   - GEMINI_API_KEY (FALLBACK SECUNDÁRIO)")
                        logger.error("   - OPENAI_API_KEY (FALLBACK TERCIÁRIO)")
                        logger.error("   - GROQ_API_KEY")
                        raise Exception("ERRO CRÍTICO: Nenhum provedor de IA disponível - verifique configuração das APIs")
                    continue
            
            provider = self.providers[provider_name]
            
            try:
                start_time = time.time()
                
                if provider_name == 'openrouter':
                    result = await self._generate_openrouter(prompt, max_tokens, temperature)
                elif provider_name == 'gemini':
                    result = await self._generate_gemini(prompt, max_tokens, temperature)
                elif provider_name == 'openai':
                    result = await self._generate_openai(prompt, max_tokens, temperature)
                elif provider_name == 'groq':
                    result = provider['client'].generate(prompt, max_tokens)
                else:
                    raise Exception(f"Provedor {provider_name} não implementado")
                
                # Registra sucesso
                provider['last_success'] = datetime.now()
                provider['consecutive_failures'] = 0
                
                processing_time = time.time() - start_time
                logger.info(f"✅ {provider_name} gerou {len(result)} caracteres em {processing_time:.2f}s")
                
                return result
                
            except Exception as e:
                # Registra falha
                provider['error_count'] += 1
                provider['consecutive_failures'] += 1
                last_error = e
                
                error_msg = str(e)
                logger.error(f"❌ Erro no {provider_name} (tentativa {attempt + 1}): {error_msg}")
                
                # CORREÇÃO: Tratamento especial para erros de 'object'
                if "object" in error_msg.lower():
                    logger.warning(f"⚠️ Erro 'object' detectado em {provider_name}, tentando próximo provedor...")
                    provider['consecutive_failures'] += 2  # Penaliza mais por erro de serialização
                
                # Desabilita provedor se muitas falhas
                if provider['consecutive_failures'] >= provider['max_errors']:
                    provider['available'] = False
                    logger.warning(f"⚠️ {provider_name} desabilitado temporariamente")
                
                # Se não é a última tentativa, continua para próximo provedor
                if attempt < max_retries - 1:
                    await asyncio.sleep(1)  # Aguarda antes de tentar novamente
                    continue
        
        # Se chegou aqui, todas as tentativas falharam
        if last_error:
            logger.error(f"❌ FALHA TOTAL: Todas as tentativas falharam. Último erro: {last_error}")
            raise last_error
        else:
            raise Exception("Falha desconhecida na geração de texto")

    async def _generate_gemini(self, prompt: str, max_tokens: int, temperature: float) -> str:
        """Gera texto usando Gemini"""
        model = genai.GenerativeModel('gemini-2.0-flash-exp')
        
        generation_config = genai.types.GenerationConfig(
            max_output_tokens=max_tokens,
            temperature=temperature,
        )
        
        response = model.generate_content(
            prompt,
            generation_config=generation_config
        )
        
        return response.text

    async def _generate_openai(self, prompt: str, max_tokens: int, temperature: float) -> str:
        """Gera texto usando OpenAI"""
        response = openai.ChatCompletion.create(
            model="gpt-4-0125-preview",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            temperature=temperature
        )
        
        return response.choices[0].message.content

    async def _generate_openrouter(self, prompt: str, max_tokens: int = 8192, temperature: float = 0.7) -> str:
        """Gera texto usando OpenRouter (Qwen 2.5 VL)"""
        provider = self.providers['openrouter']
        client = provider['client']
        
        response = client.chat.completions.create(
            model=provider['model'],  # qwen/qwen2.5-vl-32b-instruct:free
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            temperature=temperature
        )
        
        return response.choices[0].message.content

    def get_status(self) -> Dict[str, Any]:
        """Retorna status dos provedores"""
        status = {
            'total_providers': len(self.providers),
            'available_providers': sum(1 for p in self.providers.values() if p['available']),
            'providers': {}
        }
        
        for name, provider in self.providers.items():
            status['providers'][name] = {
                'available': provider['available'],
                'model': provider['model'],
                'error_count': provider['error_count'],
                'consecutive_failures': provider['consecutive_failures'],
                'last_success': provider['last_success'].isoformat() if provider['last_success'] else None,
                'supports_tools': provider.get('supports_tools', False)
            }
        
        return status

# Instância global
ai_manager = AIManager()
