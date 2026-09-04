import os
import asyncio
from telethon import TelegramClient

async def main():
    print("==========================================================")
    print("      DOWNLOADER DE MATERIAIS DO TELEGRAM - CEARÁ FINANCE ")
    print("==========================================================\n")
    
    # Solicitar credenciais de API do Telegram
    api_id_input = input("Digite seu App api_id: ").strip()
    api_hash_input = input("Digite seu App api_hash: ").strip()
    
    if not api_id_input or not api_hash_input:
        print("Erro: api_id e api_hash são obrigatórios!")
        return
        
    try:
        api_id = int(api_id_input)
    except ValueError:
        print("Erro: api_id deve ser um número inteiro!")
        return

    # ID do chat informado pelo usuário
    # URL: https://web.telegram.org/k/#-2217590850
    # No Telegram, supergrupos/canais privados usam o prefixo -100 antes do ID numérico
    chat_id = -1002217590850
    
    # Criar pasta Kenny
    output_dir = os.path.abspath("Kenny")
    os.makedirs(output_dir, exist_ok=True)
    print(f"\n[Info] Os materiais serão salvos em: {output_dir}\n")

    # Iniciar cliente
    client = TelegramClient('sessao_userbot', api_id, api_hash_input)
    
    await client.start()
    print("\n[Sucesso] Login realizado com sucesso!")

    print(f"[Telegram] Buscando mensagens no chat ID {chat_id}...")
    
    count = 0
    try:
        async for message in client.iter_messages(chat_id):
            # Verificar se a mensagem possui algum documento/arquivo de mídia
            if message.file:
                # Determinar um nome amigável para o arquivo
                filename = message.file.name
                if not filename:
                    # Gerar um nome baseado no tipo se não houver nome padrão
                    ext = message.file.ext or ".bin"
                    filename = f"arquivo_{message.id}{ext}"
                
                dest_path = os.path.join(output_dir, filename)
                
                # Evitar baixar o mesmo arquivo novamente
                if os.path.exists(dest_path):
                    print(f"[Ignorado] Já existe: {filename}")
                    continue
                
                print(f"[Download] Baixando: {filename} ({round(message.file.size / 1024 / 1024, 2)} MB)...")
                await message.download_media(file=dest_path)
                count += 1
                
        print(f"\n[Concluído] Download finalizado! Total de {count} novos arquivos salvos na pasta 'Kenny'.")
        
    except Exception as e:
        print(f"\n[Erro] Falha ao ler mensagens do chat: {e}")
        print("Verifique se o ID do chat está correto e se sua conta tem acesso a esse grupo.")
        
    finally:
        await client.disconnect()

if __name__ == '__main__':
    # Resolver loop de eventos assíncronos no Windows
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
