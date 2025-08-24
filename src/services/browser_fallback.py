#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ARQV30 Enhanced v3.0 - Browser Fallback System
Sistema de fallback para navegadores: Selenium+WebDriver → Playwright+Chromium
"""

import os
import logging
import asyncio
from typing import Dict, List, Any, Optional, Callable
from pathlib import Path
import json

logger = logging.getLogger(__name__)

class BrowserFallback:
    """Sistema de fallback para navegadores"""
    
    def __init__(self):
        """Inicializa o sistema de fallback"""
        self.selenium_available = self._check_selenium()
        self.playwright_available = self._check_playwright()
        
        logger.info(f"🌐 Browser Fallback: Selenium={self.selenium_available}, Playwright={self.playwright_available}")
    
    def _check_selenium(self) -> bool:
        """Verifica se Selenium está disponível"""
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            from selenium.webdriver.chrome.service import Service
            from webdriver_manager.chrome import ChromeDriverManager
            return True
        except ImportError:
            logger.warning("⚠️ Selenium não disponível")
            return False
    
    def _check_playwright(self) -> bool:
        """Verifica se Playwright está disponível"""
        try:
            import playwright
            from playwright.async_api import async_playwright
            return True
        except ImportError:
            logger.warning("⚠️ Playwright não disponível")
            return False
    
    async def execute_browser_task(
        self, 
        task_func: Callable,
        url: str,
        *args,
        **kwargs
    ) -> Dict[str, Any]:
        """Executa tarefa de navegador com fallback automático"""
        
        # Tenta Selenium primeiro
        if self.selenium_available:
            try:
                logger.info(f"🔧 Tentando Selenium para {url}")
                result = await self._execute_with_selenium(task_func, url, *args, **kwargs)
                if result.get('success'):
                    logger.info(f"✅ Selenium executou com sucesso")
                    return result
                else:
                    logger.warning(f"⚠️ Selenium falhou: {result.get('error', 'Erro desconhecido')}")
            except Exception as e:
                logger.error(f"❌ Erro no Selenium: {e}")
        
        # Fallback para Playwright
        if self.playwright_available:
            try:
                logger.info(f"🔧 Tentando Playwright para {url}")
                result = await self._execute_with_playwright(task_func, url, *args, **kwargs)
                if result.get('success'):
                    logger.info(f"✅ Playwright executou com sucesso")
                    return result
                else:
                    logger.warning(f"⚠️ Playwright falhou: {result.get('error', 'Erro desconhecido')}")
            except Exception as e:
                logger.error(f"❌ Erro no Playwright: {e}")
        
        # Se ambos falharam
        return {
            'success': False,
            'error': 'Todos os navegadores falharam',
            'url': url,
            'browser_used': 'none'
        }
    
    async def _execute_with_selenium(
        self, 
        task_func: Callable,
        url: str,
        *args,
        **kwargs
    ) -> Dict[str, Any]:
        """Executa tarefa com Selenium"""
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.chrome.service import Service
        from webdriver_manager.chrome import ChromeDriverManager
        
        driver = None
        try:
            # Configurações do Chrome
            options = Options()
            options.add_argument("--headless")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-gpu")
            options.add_argument("--window-size=1920,1080")
            options.add_argument("--disable-extensions")
            options.add_argument("--disable-plugins")
            options.add_argument("--disable-notifications")
            options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
            
            # Inicializa driver
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=options)
            
            # Executa tarefa personalizada
            result = await task_func(driver, url, *args, **kwargs)
            result['browser_used'] = 'selenium'
            return result
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'url': url,
                'browser_used': 'selenium'
            }
        finally:
            if driver:
                try:
                    driver.quit()
                except:
                    pass
    
    async def _execute_with_playwright(
        self, 
        task_func: Callable,
        url: str,
        *args,
        **kwargs
    ) -> Dict[str, Any]:
        """Executa tarefa com Playwright"""
        from playwright.async_api import async_playwright
        
        try:
            async with async_playwright() as p:
                # Configurações do navegador
                browser = await p.chromium.launch(
                    headless=True,
                    args=[
                        '--no-sandbox',
                        '--disable-dev-shm-usage',
                        '--disable-gpu',
                        '--disable-extensions'
                    ]
                )
                
                context = await browser.new_context(
                    viewport={'width': 1920, 'height': 1080},
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                )
                
                page = await context.new_page()
                
                # Executa tarefa personalizada
                result = await task_func(page, url, *args, **kwargs)
                result['browser_used'] = 'playwright'
                
                await browser.close()
                return result
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'url': url,
                'browser_used': 'playwright'
            }
    
    async def scrape_page(self, url: str, selectors: Dict[str, str] = None) -> Dict[str, Any]:
        """Scraping básico de página com fallback"""
        
        async def scrape_task(browser_obj, url, *args, **kwargs):
            """Tarefa de scraping adaptável para ambos os navegadores"""
            
            # Detecta tipo de navegador
            if hasattr(browser_obj, 'get'):  # Selenium
                browser_obj.get(url)
                await asyncio.sleep(3)
                
                content = {
                    'title': browser_obj.title,
                    'url': browser_obj.current_url,
                    'page_source': browser_obj.page_source[:10000]  # Limita tamanho
                }
                
                # Extrai elementos específicos se fornecidos
                if selectors:
                    from selenium.webdriver.common.by import By
                    for key, selector in selectors.items():
                        try:
                            elements = browser_obj.find_elements(By.CSS_SELECTOR, selector)
                            content[key] = [elem.text for elem in elements[:5]]  # Máximo 5 elementos
                        except:
                            content[key] = []
                
                return {
                    'success': True,
                    'content': content,
                    'url': url
                }
                
            else:  # Playwright
                await browser_obj.goto(url, wait_until='domcontentloaded')
                await asyncio.sleep(3)
                
                content = {
                    'title': await browser_obj.title(),
                    'url': browser_obj.url,
                    'page_source': (await browser_obj.content())[:10000]  # Limita tamanho
                }
                
                # Extrai elementos específicos se fornecidos
                if selectors:
                    for key, selector in selectors.items():
                        try:
                            elements = await browser_obj.query_selector_all(selector)
                            texts = []
                            for elem in elements[:5]:  # Máximo 5 elementos
                                text = await elem.text_content()
                                if text:
                                    texts.append(text)
                            content[key] = texts
                        except:
                            content[key] = []
                
                return {
                    'success': True,
                    'content': content,
                    'url': url
                }
        
        return await self.execute_browser_task(scrape_task, url, selectors=selectors)
    
    async def take_screenshot(self, url: str, output_path: str = None) -> Dict[str, Any]:
        """Captura screenshot com fallback"""
        
        if not output_path:
            output_path = f"screenshot_{int(asyncio.get_event_loop().time())}.png"
        
        async def screenshot_task(browser_obj, url, *args, **kwargs):
            """Tarefa de screenshot adaptável"""
            
            if hasattr(browser_obj, 'get'):  # Selenium
                browser_obj.get(url)
                await asyncio.sleep(3)
                
                # Captura screenshot
                browser_obj.save_screenshot(output_path)
                
                return {
                    'success': True,
                    'screenshot_path': output_path,
                    'url': url
                }
                
            else:  # Playwright
                await browser_obj.goto(url, wait_until='domcontentloaded')
                await asyncio.sleep(3)
                
                # Captura screenshot
                await browser_obj.screenshot(path=output_path, full_page=True)
                
                return {
                    'success': True,
                    'screenshot_path': output_path,
                    'url': url
                }
        
        return await self.execute_browser_task(screenshot_task, url, output_path=output_path)
    
    async def extract_images(self, url: str, limit: int = 10) -> Dict[str, Any]:
        """Extrai URLs de imagens com fallback"""
        
        async def extract_task(browser_obj, url, *args, **kwargs):
            """Tarefa de extração de imagens"""
            
            if hasattr(browser_obj, 'get'):  # Selenium
                browser_obj.get(url)
                await asyncio.sleep(3)
                
                from selenium.webdriver.common.by import By
                img_elements = browser_obj.find_elements(By.TAG_NAME, 'img')
                
                images = []
                for img in img_elements[:limit]:
                    try:
                        src = img.get_attribute('src')
                        alt = img.get_attribute('alt') or ''
                        if src and src.startswith('http'):
                            images.append({
                                'src': src,
                                'alt': alt
                            })
                    except:
                        continue
                
                return {
                    'success': True,
                    'images': images,
                    'url': url,
                    'total_found': len(images)
                }
                
            else:  # Playwright
                await browser_obj.goto(url, wait_until='domcontentloaded')
                await asyncio.sleep(3)
                
                img_elements = await browser_obj.query_selector_all('img')
                
                images = []
                for img in img_elements[:limit]:
                    try:
                        src = await img.get_attribute('src')
                        alt = await img.get_attribute('alt') or ''
                        if src and src.startswith('http'):
                            images.append({
                                'src': src,
                                'alt': alt
                            })
                    except:
                        continue
                
                return {
                    'success': True,
                    'images': images,
                    'url': url,
                    'total_found': len(images)
                }
        
        return await self.execute_browser_task(extract_task, url, limit=limit)
    
    def get_status(self) -> Dict[str, Any]:
        """Obtém status dos navegadores"""
        return {
            'selenium_available': self.selenium_available,
            'playwright_available': self.playwright_available,
            'primary_browser': 'selenium' if self.selenium_available else 'playwright' if self.playwright_available else 'none',
            'fallback_browser': 'playwright' if self.selenium_available else 'none'
        }

# Instância global
browser_fallback = BrowserFallback()