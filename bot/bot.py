import discord
from discord.ui import View, Button, Select
from discord import Embed, SelectOption
from discord import app_commands
import json
import logging
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))

try:
    from api.api import (
        add_identifiers as api_add_identifiers,
        search_warns as api_search_warns,
        delete_warn as api_delete_warn,
        get_db_connection,
        group_identifiers
    )
except ImportError as e:
    logging.error(f"無法導入API函數: {str(e)}")
    from aiohttp import web
    
    async def api_add_identifiers(request):
        return web.json_response({'error': 'API函數未正確導入'}, status=500)
    
    async def api_search_warns(request):
        return web.json_response({'error': 'API函數未正確導入'}, status=500)
    
    async def api_delete_warn(request):
        return web.json_response({'error': 'API函數未正確導入'}, status=500)
    
    def get_db_connection():
        logging.error("資料庫連接函數未正確導入")
        return None
    
    def group_identifiers(identifiers):
        return {
            'steam': [], 'license': [], 'discord': [], 'xbl': [], 'live': [], 'fivem': [], 'ip': []
        }

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PaginatorView(View):
    def __init__(self, results, interaction: discord.Interaction):
        super().__init__(timeout=300)
        self.results = results
        self.interaction = interaction
        self.current_page = 0
        self.max_page = len(results) - 1
        self.message = None
        
        self.prev_button = Button(
            label="⬅️ 上一頁", 
            style=discord.ButtonStyle.primary, 
            custom_id="prev", 
            disabled=self.current_page == 0
        )
        self.next_button = Button(
            label="➡️ 下一頁", 
            style=discord.ButtonStyle.primary, 
            custom_id="next", 
            disabled=self.current_page == self.max_page
        )
        
        self.prev_button.callback = self.prev_page_callback
        self.next_button.callback = self.next_page_callback
        
        self.add_item(self.prev_button)
        self.add_item(self.next_button)
        self.add_item(ResultSelect(results, self))

    async def interaction_check(self, interaction: discord.Interaction):
        return interaction.user.id == self.interaction.user.id

    async def on_timeout(self):
        if self.message:
            await self.message.edit(view=None)

    async def prev_page_callback(self, interaction: discord.Interaction):
        self.current_page = max(0, self.current_page - 1)
        self.update_button_state()
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

    async def next_page_callback(self, interaction: discord.Interaction):
        self.current_page = min(self.max_page, self.current_page + 1)
        self.update_button_state()
        await interaction.response.edit_message(embed=self.get_embed(), view=self)
    
    def update_button_state(self):
        self.prev_button.disabled = self.current_page == 0
        self.next_button.disabled = self.current_page == self.max_page

    def get_embed(self):
        data = self.results[self.current_page]
        embed = Embed(title="警告記錄", color=discord.Color.blue())
        embed.add_field(name="Warn ID", value=data["warn_id"], inline=False)
        embed.add_field(name="原因", value=data["warning_reason"], inline=False)
        embed.add_field(name="時間", value=data["created_at"], inline=False)
        identifiers = "\n".join([f"{k}: {', '.join(v) if v else '無'}" for k, v in data["data"].items()])
        embed.add_field(name="識別碼", value=identifiers or "無", inline=False)
        embed.set_footer(text=f"{self.current_page+1}/{self.max_page+1}")
        return embed

class ResultSelect(Select):
    def __init__(self, results, view: PaginatorView):
        options = [
            SelectOption(label=f"{i+1}. {r['warn_id']}", value=str(i)) for i, r in enumerate(results)
        ]
        super().__init__(placeholder="選擇要查看的項目", options=options)
        self.view_ref = view
        
    async def callback(self, interaction: discord.Interaction):
        self.view_ref.current_page = int(self.values[0])
        self.view_ref.update_button_state()
        await interaction.response.edit_message(embed=self.view_ref.get_embed(), view=self.view_ref)

class WarnBot(discord.Client):
    def __init__(self):
        super().__init__(intents=discord.Intents.default())
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        await self.tree.sync()
        logger.info("✅ 指令已同步")

    async def on_ready(self):
        logger.info(f"🤖 機器人已登入：{self.user}")

def extract_json_from_response(response):
    """從API響應中提取JSON數據，適應不同類型的响應對象"""
    if hasattr(response, 'text') and callable(getattr(response, 'json', None)):
        return response._body.decode('utf-8') if hasattr(response, '_body') else None
    elif hasattr(response, 'body'):
        return response.body.decode('utf-8') if isinstance(response.body, bytes) else response.body
    elif isinstance(response, dict):
        return response
    elif isinstance(response, str):
        return response
    else:
        logger.error(f"無法從響應提取JSON：{type(response)}")
        return "{}"

async def start_bot(token):
    bot = WarnBot()
    
    @bot.tree.command(name="addwarn", description="新增一筆警告記錄")
    @app_commands.describe(
        warning_reason="警告原因",
        identifiers="玩家識別碼 (以逗號分隔，例如 steam:xxx,license:yyy，可選)"
    )
    async def add_warn(interaction: discord.Interaction, warning_reason: str, identifiers: str = ""):
        try:
            identifiers_list = [id.strip() for id in identifiers.split(",") if id.strip()] if identifiers else []
            
            request_data = {
                'identifiers': identifiers_list,
                'warning_reason': warning_reason
            }
            
            class MockRequest:
                async def json(self):
                    return request_data
            
            response = await api_add_identifiers(MockRequest())
            
            json_str = extract_json_from_response(response)
            response_data = json.loads(json_str)
            status = getattr(response, 'status', 201)
            
            if status == 201:
                embed = discord.Embed(title="警告記錄新增成功", color=discord.Color.green())
                embed.add_field(name="Warn ID", value=response_data["warn_id"], inline=False)
                embed.add_field(name="原因", value=response_data["warning_reason"], inline=False)
                
                identifiers_text = "\n".join([
                    f"{k}: {', '.join(v)}" for k, v in response_data["data"].items() if v
                ]) or "無"
                embed.add_field(name="識別碼", value=identifiers_text, inline=False)
                embed.set_footer(text=f"記錄 ID: {response_data['id']}")
                
                await interaction.response.send_message(embed=embed)
            else:
                embed = discord.Embed(
                    title="警告新增失敗",
                    description=f"錯誤: {response_data.get('error', '未知錯誤')}",
                    color=discord.Color.red()
                )
                await interaction.response.send_message(embed=embed)
                
        except Exception as e:
            logger.error(f"新增警告錯誤：{str(e)}")
            embed = discord.Embed(title="錯誤", description=f"發生錯誤: {str(e)}", color=discord.Color.red())
            await interaction.response.send_message(embed=embed)

    @bot.tree.command(name="searchwarn", description="搜尋警告記錄")
    @app_commands.describe(keyword="關鍵字（Warn ID / 原因 / 識別碼）")
    async def searchwarn(interaction: discord.Interaction, keyword: str):
        try:
            if len(keyword.strip()) < 2:
                await interaction.response.send_message("請輸入至少 2 個字元的關鍵字", ephemeral=True)
                return
            
            class MockRequest:
                @property
                def query(self):
                    return {'keyword': keyword}
            
            response = await api_search_warns(MockRequest())
            
            json_str = extract_json_from_response(response)
            response_data = json.loads(json_str)
            status = getattr(response, 'status', 200) 
            
            if status == 200 and response_data.get('success', False) and response_data.get('count', 0) > 0:
                results = response_data['result']
                view = PaginatorView(results, interaction)
                embed = view.get_embed()
                await interaction.response.send_message(embed=embed, view=view)
                view.message = await interaction.original_response()
            else:
                await interaction.response.send_message("❌ 找不到相關結果", ephemeral=True)
                
        except Exception as e:
            logger.error(f"搜尋錯誤：{str(e)}")
            await interaction.response.send_message("🚨 搜尋時發生錯誤", ephemeral=True)

    @bot.tree.command(name="deletewarn", description="刪除指定 Warn ID 的警告記錄")
    @app_commands.describe(warn_id="要刪除的 Warn ID")
    async def delete_warn(interaction: discord.Interaction, warn_id: str):
        try:
            class MockRequest:
                @property
                def match_info(self):
                    return {'warn_id': warn_id}
            
            response = await api_delete_warn(MockRequest())
            
            json_str = extract_json_from_response(response)
            response_data = json.loads(json_str)
            status = getattr(response, 'status', 200)
            
            if status == 200 and response_data.get('success', False):
                embed = discord.Embed(
                    title="刪除成功", 
                    description=f"已刪除 Warn ID: {warn_id}", 
                    color=discord.Color.green()
                )
                await interaction.response.send_message(embed=embed)
            else:
                embed = discord.Embed(
                    title="刪除失敗", 
                    description=f"錯誤: {response_data.get('error', response_data.get('message', '未知錯誤'))}", 
                    color=discord.Color.red()
                )
                await interaction.response.send_message(embed=embed)
                
        except Exception as e:
            logger.error(f"刪除錯誤：{str(e)}")
            embed = discord.Embed(title="錯誤", description=f"發生錯誤: {str(e)}", color=discord.Color.red())
            await interaction.response.send_message(embed=embed)

    try:
        await bot.start(token)
    except Exception as e:
        logger.error(f"機器人啟動失敗: {str(e)}")
        raise