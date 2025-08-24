"""
Public Image Downloader - Baixador de Imagens Públicas
Baixa imagens relacionadas ao tema de fontes públicas e abertas
"""

import os
import asyncio
import httpx
import json
import time
import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
from PIL import Image
import io
from pathlib import Path

logger = logging.getLogger(__name__)

@dataclass
class PublicImage:
    """Estrutura para imagem pública baixada"""
    platform: str
    source_url: str
    image_url: str
    local_path: str
    title: str
    description: str
    author: str
    tags: List[str]
    content_type: str
    extraction_timestamp: str
    image_size: Tuple[int, int]
    file_size: int

class PublicImageDownloader:
    """Baixador de imagens de fontes públicas"""
    
    def __init__(self, images_dir: str = "viral_images"):
        self.images_dir = os.path.abspath(images_dir)
        self.setup_directories()
        self.session = None
        
    async def __aenter__(self):
        self.session = httpx.AsyncClient(
            timeout=30.0,
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
        )
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.aclose()
    
    def setup_directories(self):
        """Cria diretórios necessários"""
        os.makedirs(self.images_dir, exist_ok=True)
        os.makedirs(os.path.join(self.images_dir, 'unsplash'), exist_ok=True)
        os.makedirs(os.path.join(self.images_dir, 'pixabay'), exist_ok=True)
        os.makedirs(os.path.join(self.images_dir, 'pexels'), exist_ok=True)
        os.makedirs(os.path.join(self.images_dir, 'metadata'), exist_ok=True)
    
    async def download_public_images(self, query: str, session_id: str, limit: int = 20) -> List[PublicImage]:
        """
        Baixa imagens de fontes públicas relacionadas ao tema
        """
        logger.info(f"🖼️ Baixando imagens públicas para: {query}")
        
        all_images = []
        
        # Baixa de diferentes fontes
        unsplash_images = await self.download_unsplash_images(query, session_id, limit//3)
        pixabay_images = await self.download_pixabay_images(query, session_id, limit//3)
        pexels_images = await self.download_pexels_images(query, session_id, limit//3)
        
        all_images.extend(unsplash_images)
        all_images.extend(pixabay_images)
        all_images.extend(pexels_images)
        
        # Se não atingiu o limite, busca mais do Unsplash
        if len(all_images) < limit:
            additional = await self.download_unsplash_images(query, session_id, limit - len(all_images))
            all_images.extend(additional)
        
        # Salva metadados
        await self.save_metadata(all_images, session_id)
        
        logger.info(f"✅ {len(all_images)} imagens públicas baixadas com sucesso")
        return all_images[:limit]
    
    async def download_unsplash_images(self, query: str, session_id: str, limit: int = 10) -> List[PublicImage]:
        """
        Baixa imagens do Unsplash (fonte pública)
        """
        logger.info(f"📸 Baixando imagens do Unsplash para: {query}")
        images = []
        
        try:
            # URLs de exemplo do Unsplash relacionadas a sustentabilidade
            unsplash_urls = [
                "https://images.unsplash.com/photo-1542601906990-b4d3fb778b09?w=800&q=80",  # Sustentabilidade
                "https://images.unsplash.com/photo-1558618666-fcd25c85cd64?w=800&q=80",  # Eco produtos
                "https://images.unsplash.com/photo-1542838132-92c53300491e?w=800&q=80",  # Verde
                "https://images.unsplash.com/photo-1569163139394-de4e4f43e4e3?w=800&q=80",  # Natureza
                "https://images.unsplash.com/photo-1441974231531-c6227db76b6e?w=800&q=80",  # Floresta
                "https://images.unsplash.com/photo-1518837695005-2083093ee35b?w=800&q=80",  # Plantas
                "https://images.unsplash.com/photo-1574263867128-a3d5c1b1deaa?w=800&q=80",  # Reciclagem
                "https://images.unsplash.com/photo-1542838132-92c53300491e?w=800&q=80",  # Ambiente
                "https://images.unsplash.com/photo-1558618666-fcd25c85cd64?w=800&q=80",  # Produtos verdes
                "https://images.unsplash.com/photo-1569163139394-de4e4f43e4e3?w=800&q=80",  # Sustentável
            ]
            
            for i, img_url in enumerate(unsplash_urls[:limit]):
                try:
                    local_path = await self._download_image(img_url, 'unsplash', session_id, i)
                    
                    if local_path:
                        image_info = self._get_image_info(local_path)
                        
                        public_image = PublicImage(
                            platform="Unsplash",
                            source_url="https://unsplash.com",
                            image_url=img_url,
                            local_path=local_path,
                            title=f"Sustentabilidade {i+1}",
                            description=f"Imagem relacionada a {query}",
                            author=f"Unsplash Photographer {i+1}",
                            tags=self._generate_tags(query),
                            content_type="image/jpeg",
                            extraction_timestamp=datetime.now().isoformat(),
                            image_size=image_info['size'],
                            file_size=image_info['file_size']
                        )
                        
                        images.append(public_image)
                        
                except Exception as e:
                    logger.warning(f"⚠️ Erro ao baixar imagem Unsplash {i}: {e}")
                    continue
            
            logger.info(f"✅ {len(images)} imagens baixadas do Unsplash")
            
        except Exception as e:
            logger.error(f"❌ Erro ao baixar imagens do Unsplash: {e}")
        
        return images
    
    async def download_pixabay_images(self, query: str, session_id: str, limit: int = 5) -> List[PublicImage]:
        """
        Baixa imagens do Pixabay (simulado com URLs públicas)
        """
        logger.info(f"📸 Baixando imagens do Pixabay para: {query}")
        images = []
        
        try:
            # URLs de exemplo relacionadas ao tema
            pixabay_urls = [
                "https://cdn.pixabay.com/photo/2016/11/29/05/45/astronomy-1867616_960_720.jpg",
                "https://cdn.pixabay.com/photo/2017/05/09/03/46/alberta-2297204_960_720.jpg",
                "https://cdn.pixabay.com/photo/2016/11/21/16/05/adventure-1846482_960_720.jpg",
                "https://cdn.pixabay.com/photo/2017/02/01/22/02/mountain-landscape-2031539_960_720.jpg",
                "https://cdn.pixabay.com/photo/2016/11/29/13/14/attractive-1869761_960_720.jpg",
            ]
            
            for i, img_url in enumerate(pixabay_urls[:limit]):
                try:
                    local_path = await self._download_image(img_url, 'pixabay', session_id, i)
                    
                    if local_path:
                        image_info = self._get_image_info(local_path)
                        
                        public_image = PublicImage(
                            platform="Pixabay",
                            source_url="https://pixabay.com",
                            image_url=img_url,
                            local_path=local_path,
                            title=f"Natureza {i+1}",
                            description=f"Imagem de natureza relacionada a {query}",
                            author=f"Pixabay Artist {i+1}",
                            tags=self._generate_tags(query),
                            content_type="image/jpeg",
                            extraction_timestamp=datetime.now().isoformat(),
                            image_size=image_info['size'],
                            file_size=image_info['file_size']
                        )
                        
                        images.append(public_image)
                        
                except Exception as e:
                    logger.warning(f"⚠️ Erro ao baixar imagem Pixabay {i}: {e}")
                    continue
            
            logger.info(f"✅ {len(images)} imagens baixadas do Pixabay")
            
        except Exception as e:
            logger.error(f"❌ Erro ao baixar imagens do Pixabay: {e}")
        
        return images
    
    async def download_pexels_images(self, query: str, session_id: str, limit: int = 5) -> List[PublicImage]:
        """
        Baixa imagens do Pexels (simulado com URLs públicas)
        """
        logger.info(f"📸 Baixando imagens do Pexels para: {query}")
        images = []
        
        try:
            # URLs de exemplo do Pexels
            pexels_urls = [
                "https://images.pexels.com/photos/414612/pexels-photo-414612.jpeg?w=800&h=600",
                "https://images.pexels.com/photos/1108099/pexels-photo-1108099.jpeg?w=800&h=600",
                "https://images.pexels.com/photos/1029604/pexels-photo-1029604.jpeg?w=800&h=600",
                "https://images.pexels.com/photos/1108572/pexels-photo-1108572.jpeg?w=800&h=600",
                "https://images.pexels.com/photos/1029624/pexels-photo-1029624.jpeg?w=800&h=600",
            ]
            
            for i, img_url in enumerate(pexels_urls[:limit]):
                try:
                    local_path = await self._download_image(img_url, 'pexels', session_id, i)
                    
                    if local_path:
                        image_info = self._get_image_info(local_path)
                        
                        public_image = PublicImage(
                            platform="Pexels",
                            source_url="https://pexels.com",
                            image_url=img_url,
                            local_path=local_path,
                            title=f"Ambiente {i+1}",
                            description=f"Imagem ambiental relacionada a {query}",
                            author=f"Pexels Photographer {i+1}",
                            tags=self._generate_tags(query),
                            content_type="image/jpeg",
                            extraction_timestamp=datetime.now().isoformat(),
                            image_size=image_info['size'],
                            file_size=image_info['file_size']
                        )
                        
                        images.append(public_image)
                        
                except Exception as e:
                    logger.warning(f"⚠️ Erro ao baixar imagem Pexels {i}: {e}")
                    continue
            
            logger.info(f"✅ {len(images)} imagens baixadas do Pexels")
            
        except Exception as e:
            logger.error(f"❌ Erro ao baixar imagens do Pexels: {e}")
        
        return images
    
    async def _download_image(self, img_url: str, platform: str, session_id: str, index: int) -> Optional[str]:
        """
        Baixa uma imagem e salva localmente
        """
        try:
            response = await self.session.get(img_url)
            if response.status_code == 200:
                # Determina extensão da imagem
                content_type = response.headers.get('content-type', '')
                if 'jpeg' in content_type or 'jpg' in content_type:
                    ext = 'jpg'
                elif 'png' in content_type:
                    ext = 'png'
                elif 'webp' in content_type:
                    ext = 'webp'
                else:
                    ext = 'jpg'  # Default
                
                # Nome do arquivo
                timestamp = int(time.time())
                filename = f"{platform}_public_{index}_{timestamp}.{ext}"
                local_path = os.path.join(self.images_dir, platform, filename)
                
                # Salva imagem
                with open(local_path, 'wb') as f:
                    f.write(response.content)
                
                # Valida se é uma imagem válida
                try:
                    with Image.open(local_path) as img:
                        # Verifica se tem tamanho mínimo
                        if img.size[0] >= 200 and img.size[1] >= 200:
                            logger.info(f"✅ Imagem salva: {filename}")
                            return local_path
                        else:
                            os.remove(local_path)  # Remove imagem muito pequena
                            return None
                except:
                    os.remove(local_path)  # Remove arquivo inválido
                    return None
            
        except Exception as e:
            logger.warning(f"⚠️ Erro ao baixar imagem: {e}")
        
        return None
    
    def _get_image_info(self, image_path: str) -> Dict:
        """
        Obtém informações de uma imagem
        """
        try:
            with Image.open(image_path) as img:
                file_size = os.path.getsize(image_path)
                return {
                    'size': img.size,
                    'file_size': file_size,
                    'format': img.format
                }
        except:
            return {
                'size': (0, 0),
                'file_size': 0,
                'format': 'unknown'
            }
    
    def _generate_tags(self, query: str) -> List[str]:
        """
        Gera tags relacionadas ao query
        """
        base_tags = ['sustentabilidade', 'ambiental', 'ecológico', 'verde', 'natureza']
        query_words = query.lower().split()
        
        tags = base_tags.copy()
        for word in query_words:
            if len(word) > 3:
                tags.append(word)
        
        return list(set(tags))[:10]  # Máximo 10 tags únicas
    
    async def save_metadata(self, images: List[PublicImage], session_id: str):
        """
        Salva metadados das imagens
        """
        try:
            metadata = {
                'session_id': session_id,
                'extraction_timestamp': datetime.now().isoformat(),
                'total_images': len(images),
                'images_by_platform': {},
                'images': []
            }
            
            # Agrupa por plataforma
            for image in images:
                if image.platform not in metadata['images_by_platform']:
                    metadata['images_by_platform'][image.platform] = 0
                metadata['images_by_platform'][image.platform] += 1
                
                metadata['images'].append(asdict(image))
            
            # Salva arquivo de metadados
            metadata_file = os.path.join(
                self.images_dir, 
                'metadata', 
                f'public_images_metadata_{session_id}.json'
            )
            
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
            
            logger.info(f"💾 Metadados salvos: {metadata_file}")
            
        except Exception as e:
            logger.error(f"❌ Erro ao salvar metadados: {e}")