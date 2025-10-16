import time
import json
import os
from datetime import datetime
from discord_webhook import DiscordWebhook, DiscordEmbed
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException

class LoLDefeatMonitor:
    def __init__(self, webhook_url, summoner_url, check_interval=300):
        """
        Args:
            webhook_url: URL del webhook de Discord
            summoner_url: URL del perfil de OP.GG
            check_interval: Intervalo de comprobación en segundos (default: 5 minutos)
        """
        self.webhook_url = webhook_url
        self.summoner_url = summoner_url
        self.check_interval = check_interval
        self.stats_file = "defeat_stats.json"
        self.last_match_time = None
        self.stats = self.load_stats()
        self.driver = None
        self.first_run = True
        
        # Mensajes graciosos para derrotas
        self.defeat_messages = [
            "🤡 Otra al saco de las derrotas",
            "💀 F en el chat",
            "🎪 El circo ha vuelto a la ciudad",
            "🤦 Buff diff obvio",
            "🎭 Shakespeare escribiría tragedias sobre esto",
            "🎪 Más show que Broadway",
            "💩 Diff de gaming chair",
            "🤡 Clown fiesta deluxe",
            "🎰 Perdiendo más rápido que en el casino",
            "🎢 Montaña rusa... pero solo va para abajo",
            "🎪 El circo Kekles sigue de gira",
            "💀 Speedrun any% a Hierro",
            "🤮 Mis ojos sangran",
            "🎭 Mejor actuar en películas de terror",
            "🤦‍♂️ Report jg diff (wait...)",
            "🎯 Miss click en champion select",
            "🍿 Esto merece palomitas",
            "🤡 El meme viviente",
            "💀 Más muerto que la season 8",
            "🎪 Circo Kekles: Función continua"
        ]
    
    def setup_driver(self):
        """Configura el driver de Selenium"""
        chrome_options = Options()
        chrome_options.add_argument('--headless')  # Ejecutar sin ventana
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
        
        try:
            self.driver = webdriver.Chrome(options=chrome_options)
            print("✅ Driver de Chrome iniciado correctamente")
        except Exception as e:
            print(f"❌ Error al iniciar Chrome: {e}")
            print("💡 Asegúrate de tener ChromeDriver instalado")
            raise
    
    def load_stats(self):
        """Carga las estadísticas desde el archivo JSON"""
        if os.path.exists(self.stats_file):
            with open(self.stats_file, 'r') as f:
                return json.load(f)
        return {
            "total_defeats": 0,
            "current_streak": 0,
            "max_streak": 0,
            "last_check": None
        }
    
    def save_stats(self):
        """Guarda las estadísticas en el archivo JSON"""
        with open(self.stats_file, 'w') as f:
            json.dump(self.stats, f, indent=2)
    
    def get_latest_match(self):
        """Obtiene información de la última partida usando Selenium"""
        try:
            print("⏳ Cargando página...")
            self.driver.get(self.summoner_url)
            
            # Esperar a que carguen las partidas
            wait = WebDriverWait(self.driver, 15)
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.flex.flex-col")))
            
            # Dar tiempo extra para que cargue todo
            time.sleep(3)
            
            print("✅ Página cargada, buscando partidas...")
            
            # Buscar todos los contenedores de partidas individuales
            match_containers = self.driver.find_elements(By.XPATH, "//div[contains(@class, 'box-border') and contains(@class, 'flex') and contains(@class, 'w-full') and contains(@class, 'border-l-[6px]')]")
            
            if not match_containers:
                print("❌ No se encontraron partidas")
                return None
            
            print(f"✅ Encontradas {len(match_containers)} partidas")
            
            # Obtener la primera partida (más reciente)
            match_container = match_containers[0]
            
            # Detectar si es victoria o derrota
            try:
                defeat_elem = match_container.find_element(By.XPATH, ".//strong[contains(text(), 'Defeat')]")
                is_defeat = True
                result = "Defeat"
                print("🔴 Detectada: DERROTA")
            except NoSuchElementException:
                try:
                    victory_elem = match_container.find_element(By.XPATH, ".//strong[contains(text(), 'Victory')]")
                    is_defeat = False
                    result = "Victory"
                    print("🟢 Detectada: VICTORIA")
                except NoSuchElementException:
                    print("⚠️ No se pudo determinar el resultado")
                    return None
            
            # Obtener timestamp
            try:
                time_elem = match_container.find_element(By.CSS_SELECTOR, "span[data-tooltip-content*='/2025']")
                match_time = time_elem.get_attribute('data-tooltip-content')
                print(f"🕒 Timestamp: {match_time}")
            except:
                match_time = datetime.now().strftime('%d/%m/%Y, %H:%M')
                print(f"⚠️ Usando timestamp actual: {match_time}")
            
            # Obtener campeón
            try:
                champion_img = match_container.find_element(By.CSS_SELECTOR, "img[alt]:not([alt=''])")
                champion = champion_img.get_attribute('alt')
                print(f"🎮 Campeón: {champion}")
            except:
                champion = "Unknown"
                print("⚠️ Campeón no encontrado")
            
            # Obtener KDA
            try:
                kda_elements = match_container.find_elements(By.CSS_SELECTOR, "div.flex.items-center.gap-1 strong")
                if len(kda_elements) >= 3:
                    kills = kda_elements[0].text
                    deaths = kda_elements[1].text
                    assists = kda_elements[2].text
                    print(f"📊 KDA: {kills}/{deaths}/{assists}")
                else:
                    kills = deaths = assists = "?"
            except:
                kills = deaths = assists = "?"
                print("⚠️ KDA no encontrado")
            
            # Obtener duración
            try:
                duration_elem = match_container.find_element(By.XPATH, ".//span[contains(text(), 'm') and contains(text(), 's')]")
                duration = duration_elem.text
                print(f"⏱️ Duración: {duration}")
            except:
                duration = "?"
                print("⚠️ Duración no encontrada")
            
            return {
                'is_defeat': is_defeat,
                'result': result,
                'timestamp': match_time,
                'champion': champion,
                'kills': kills,
                'deaths': deaths,
                'assists': assists,
                'duration': duration
            }
            
        except TimeoutException:
            print("⏱️ Timeout esperando que cargue la página")
            return None
        except Exception as e:
            print(f"❌ Error al obtener datos: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def get_all_recent_matches(self, limit=20):
        """Obtiene todas las partidas recientes del historial"""
        try:
            print("⏳ Cargando historial completo...")
            self.driver.get(self.summoner_url)
            
            wait = WebDriverWait(self.driver, 15)
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.flex.flex-col")))
            time.sleep(3)
            
            # Buscar todos los contenedores de partidas individuales
            match_containers = self.driver.find_elements(By.XPATH, "//div[contains(@class, 'box-border') and contains(@class, 'flex') and contains(@class, 'w-full') and contains(@class, 'border-l-[6px]')]")
            
            if not match_containers:
                return []
            
            matches = []
            for i, container in enumerate(match_containers[:limit]):
                try:
                    # Detectar resultado
                    try:
                        container.find_element(By.XPATH, ".//strong[contains(text(), 'Defeat')]")
                        is_defeat = True
                    except:
                        is_defeat = False
                    
                    if not is_defeat:
                        continue
                    
                    # Obtener timestamp
                    try:
                        time_elem = container.find_element(By.CSS_SELECTOR, "span[data-tooltip-content*='/2025']")
                        match_time = time_elem.get_attribute('data-tooltip-content')
                    except:
                        match_time = f"Partida {i+1}"
                    
                    # Obtener campeón
                    try:
                        champion_img = container.find_element(By.CSS_SELECTOR, "img[alt]:not([alt=''])")
                        champion = champion_img.get_attribute('alt')
                    except:
                        champion = "Unknown"
                    
                    # Obtener KDA
                    try:
                        kda_elements = container.find_elements(By.CSS_SELECTOR, "div.flex.items-center.gap-1 strong")
                        if len(kda_elements) >= 3:
                            kills = kda_elements[0].text
                            deaths = kda_elements[1].text
                            assists = kda_elements[2].text
                        else:
                            kills = deaths = assists = "?"
                    except:
                        kills = deaths = assists = "?"
                    
                    matches.append({
                        'champion': champion,
                        'kills': kills,
                        'deaths': deaths,
                        'assists': assists,
                        'timestamp': match_time
                    })
                    
                except Exception as e:
                    print(f"⚠️ Error procesando partida {i+1}: {e}")
                    continue
            
            return matches
            
        except Exception as e:
            print(f"❌ Error obteniendo historial: {e}")
            return []
    
    def send_initial_summary(self, recent_defeats):
        """Envía un resumen inicial de las derrotas recientes"""
        webhook = DiscordWebhook(url=self.webhook_url, username='LoL Defeat Tracker')
        
        embed = DiscordEmbed(
            title='🚀 Bot Iniciado - Resumen de Derrotas Recientes',
            description='Aquí están las derrotas más recientes en el historial:',
            color='FFA500'
        )
        
        if not recent_defeats:
            embed.add_embed_field(
                name='✅ Sin derrotas recientes',
                value='No se encontraron derrotas en el historial reciente',
                inline=False
            )
        else:
            # Mostrar hasta 5 derrotas más recientes
            defeats_text = ""
            for i, match in enumerate(recent_defeats[:5], 1):
                defeats_text += f"**{i}.** {match['champion']} - {match['kills']}/{match['deaths']}/{match['assists']}\n"
            
            embed.add_embed_field(
                name=f'💀 Últimas {min(5, len(recent_defeats))} Derrotas',
                value=defeats_text,
                inline=False
            )
            
            embed.add_embed_field(
                name='📊 Total de Derrotas Recientes',
                value=f"**{len(recent_defeats)}** derrotas en las últimas 20 partidas",
                inline=False
            )
        
        embed.add_embed_field(
            name='📈 Estadísticas Guardadas',
            value=f"**Total:** {self.stats['total_defeats']} derrotas\n"
                  f"**Racha actual:** {self.stats['current_streak']}\n"
                  f"**Record:** {self.stats['max_streak']}",
            inline=False
        )
        
        embed.add_embed_field(
            name='👀 Monitorización',
            value='El bot ahora está monitorizando nuevas partidas...',
            inline=False
        )
        
        embed.set_timestamp()
        webhook.add_embed(embed)
        
        try:
            webhook.execute()
            print(f"✅ Resumen inicial enviado a Discord")
        except Exception as e:
            print(f"❌ Error al enviar resumen inicial: {e}")
    
    def send_defeat_notification(self, match_info):
        """Envía notificación de derrota a Discord"""
        import random
        
        message = random.choice(self.defeat_messages)
        
        webhook = DiscordWebhook(url=self.webhook_url, username='LoL Defeat Tracker')
        
        # Crear embed
        embed = DiscordEmbed(
            title=f'💀 DERROTA DETECTADA 💀',
            description=message,
            color='FF0000'
        )
        
        # Añadir campos
        embed.add_embed_field(
            name='📊 Estadísticas de la Partida',
            value=f"**Campeón:** {match_info['champion']}\n"
                  f"**KDA:** {match_info['kills']}/{match_info['deaths']}/{match_info['assists']}\n"
                  f"**Duración:** {match_info['duration']}",
            inline=False
        )
        
        embed.add_embed_field(
            name='🔥 Racha Actual de Derrotas',
            value=f"**{self.stats['current_streak']}** partidas perdidas seguidas",
            inline=True
        )
        
        embed.add_embed_field(
            name='📈 Total de Derrotas',
            value=f"**{self.stats['total_defeats']}** derrotas registradas",
            inline=True
        )
        
        if self.stats['current_streak'] >= 3:
            embed.add_embed_field(
                name='⚠️ ALERTA',
                value=f"🚨 LOSING STREAK DE {self.stats['current_streak']} PARTIDAS 🚨",
                inline=False
            )
        
        # Añadir record si existe
        if self.stats['max_streak'] > 0:
            embed.add_embed_field(
                name='🏆 Record de Losing Streak',
                value=f"**{self.stats['max_streak']}** derrotas consecutivas",
                inline=False
            )
        
        embed.set_footer(text=f"Timestamp: {match_info['timestamp']}")
        embed.set_timestamp()
        
        webhook.add_embed(embed)
        
        try:
            response = webhook.execute()
            print(f"✅ Notificación enviada a Discord")
        except Exception as e:
            print(f"❌ Error al enviar a Discord: {e}")
    
    def send_victory_notification(self, match_info):
        """Envía notificación cuando se rompe la racha de derrotas"""
        if self.stats['current_streak'] >= 3:
            webhook = DiscordWebhook(url=self.webhook_url, username='LoL Defeat Tracker')
            
            embed = DiscordEmbed(
                title='🎉 ¡VICTORIA!',
                description=f"Se acabó la racha de {self.stats['current_streak']} derrotas 🎊",
                color='00FF00'
            )
            
            embed.add_embed_field(
                name='📊 Estadísticas de la Partida',
                value=f"**Campeón:** {match_info['champion']}\n"
                      f"**KDA:** {match_info['kills']}/{match_info['deaths']}/{match_info['assists']}\n"
                      f"**Duración:** {match_info['duration']}",
                inline=False
            )
            
            embed.set_timestamp()
            webhook.add_embed(embed)
            
            try:
                webhook.execute()
                print(f"✅ Notificación de victoria enviada")
            except Exception as e:
                print(f"❌ Error al enviar victoria: {e}")
    
    def run(self):
        """Ejecuta el monitor continuamente"""
        print(f"🚀 Monitor iniciado")
        print(f"📊 Estadísticas actuales:")
        print(f"   - Total derrotas: {self.stats['total_defeats']}")
        print(f"   - Racha actual: {self.stats['current_streak']}")
        print(f"   - Racha máxima: {self.stats['max_streak']}")
        print(f"⏱️  Comprobando cada {self.check_interval} segundos")
        print(f"🔗 URL: {self.summoner_url}\n")
        
        # Inicializar el driver
        self.setup_driver()
        
        try:
            # En la primera ejecución, enviar resumen de derrotas recientes
            if self.first_run:
                print(f"\n{'='*60}")
                print("📋 Primera ejecución - Analizando historial...")
                print(f"{'='*60}\n")
                
                recent_defeats = self.get_all_recent_matches(limit=20)
                print(f"✅ Encontradas {len(recent_defeats)} derrotas en el historial reciente")
                
                self.send_initial_summary(recent_defeats)
                self.first_run = False
                
                # Obtener la última partida para iniciar el tracking
                latest = self.get_latest_match()
                if latest:
                    self.last_match_time = latest['timestamp']
                    print(f"🎯 Última partida registrada: {latest['timestamp']}")
                
                print(f"\n{'='*60}")
                print("✅ Inicialización completa - Comenzando monitorización")
                print(f"{'='*60}\n")
            
            while True:
                try:
                    print(f"\n{'='*60}")
                    print(f"🔍 Comprobando partidas... [{datetime.now().strftime('%H:%M:%S')}]")
                    print(f"{'='*60}")
                    
                    match = self.get_latest_match()
                    
                    if match and match['timestamp'] != self.last_match_time:
                        print(f"\n🆕 Nueva partida detectada: {match['result']}")
                        
                        if match['is_defeat']:
                            # Es una derrota
                            self.stats['total_defeats'] += 1
                            self.stats['current_streak'] += 1
                            
                            if self.stats['current_streak'] > self.stats['max_streak']:
                                self.stats['max_streak'] = self.stats['current_streak']
                            
                            self.send_defeat_notification(match)
                            print(f"💀 DERROTA #{self.stats['total_defeats']} | Racha: {self.stats['current_streak']}")
                        else:
                            # Es una victoria
                            self.send_victory_notification(match)
                            print(f"✅ Victoria - Racha de derrotas reiniciada")
                            self.stats['current_streak'] = 0
                        
                        self.last_match_time = match['timestamp']
                        self.stats['last_check'] = datetime.now().isoformat()
                        self.save_stats()
                    else:
                        print(f"✓ Sin cambios - Última partida ya registrada")
                    
                    print(f"\n⏳ Esperando {self.check_interval} segundos hasta la próxima comprobación...")
                    time.sleep(self.check_interval)
                    
                except Exception as e:
                    print(f"❌ Error en el ciclo: {e}")
                    time.sleep(self.check_interval)
                    
        except KeyboardInterrupt:
            print("\n\n👋 Monitor detenido por el usuario")
        finally:
            if self.driver:
                self.driver.quit()
                print("🔒 Driver cerrado")

# Ejemplo de uso
if __name__ == "__main__":
    # Configuración
    # Obtener configuración desde .env
    DISCORD_WEBHOOK_URL = os.getenv('DISCORD_WEBHOOK_URL')
    SUMMONER_URL = os.getenv('SUMMONER_URL')
    CHECK_INTERVAL = int(os.getenv('CHECK_INTERVAL', 300))  # 300 por defecto si no existe
    
    # Validar que las variables existen
    if not DISCORD_WEBHOOK_URL:
        print("❌ ERROR: DISCORD_WEBHOOK_URL no está configurado en .env")
        exit(1)
    if not SUMMONER_URL:
        print("❌ ERROR: SUMMONER_URL no está configurado en .env")
        exit(1)
    
    print("✅ Configuración cargada desde .env")
    # Crear y ejecutar el monitor
    monitor = LoLDefeatMonitor(
        webhook_url=DISCORD_WEBHOOK_URL,
        summoner_url=SUMMONER_URL,
        check_interval=CHECK_INTERVAL
    )
    
    monitor.run()