from twitchio.ext import commands
from langchain_ollama import ChatOllama
from langchain_core.messages import AIMessage
from langchain_core.prompts import ChatPromptTemplate
import os
import argparse

# arg parse boiler plate
parser = argparse.ArgumentParser(description='Twitch Chat Bot')
# add arguments: model, temperature, num_predict, history_length
parser.add_argument('--model', type=str, default='llama3.2', help='Model name')
parser.add_argument('--temperature', type=float, default=0.4, help='Sampling temperature')
parser.add_argument('--num_predict', type=int, default=128, help='Number of tokens to predict')
parser.add_argument('--history_length', type=int, default=8, help='Number of messages to keep in history')
args = parser.parse_args()
# fetch arguments
model = args.model
temperature = args.temperature
num_predict = args.num_predict
history_length = args.history_length


llm = ChatOllama(
    model=model,
    temperature=temperature,
    num_predict=num_predict,
)

token = os.environ.get('TWITCHIO_TOKEN')


class Bot(commands.Bot):
    
    def __init__(self, token, llm, initial_channels=['mkzxd']):
        super().__init__(token=token, prefix='?', initial_channels=initial_channels)
        self.llm = llm
        self.self_ignore = True
        self.chat_history = {}  # Dicionário para armazenar o histórico do chat por usuário
        
        self.prompt = lambda history: ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "Você é um chatbot de uma live de Valorant na TwitchTV. Seu idioma é português do Brasil. O histórico de conversa com o usuário {chat_user} é:\n" + history + "\nResponda ao usuário atual: {chat_user}"
                ),
                ("human", "{input}"),
            ]
        )

        # Gera a resposta da LLM com o histórico do usuário
        self.chain = lambda history: self.prompt(history) | self.llm        

    async def event_ready(self):
        print(f'Logged in as | {self.nick}')
        print(f'User id is | {self.user_id}')

    async def event_join(self, channel, user):
        # prompt = ChatPromptTemplate([(
        #             "system",
        #             "Você é um chatbot de uma live de Valorant na TwitchTV. Seu idioma é português do Brasil. O usuário {chat_user} acabou de entrar na live. Dê maravilhosas boas-vindas a ele!"
        #             )])

        # chain = prompt | self.llm
        # print(f'{user} joined channel | {channel}')
        # ai_msg = chain.invoke({'chat_user': user})
        prompt = [(
                    "system",
                    f"Você é um chatbot de uma live de Valorant na TwitchTV. Seu idioma é português do Brasil. O usuário {user} acabou de entrar no chat. Dê maravilhosas boas-vindas a ele!"
                    )]
        
        
        print(f'{user} joined channel | {channel}')
        ai_msg = self.llm.invoke(prompt)        
        print(ai_msg.content)
        await channel.send(f"{ai_msg.content}")
        
        
    async def event_message(self, message):
        # Ignore messages enviadas pelo próprio bot
        if message.echo:
            return
        elif message.author.name == self.nick:
            if self.self_ignore:
                await self.handle_commands(message)
                return
            else:
                self.self_ignore = True
        
        user = message.author.name
        user_input = message.content
        
        # Adiciona o histórico do usuário ao prompt se ele existir
        if user not in self.chat_history:
            self.chat_history[user] = []
        
        # Limita o histórico para as últimas 5 mensagens
        self.chat_history[user] = (self.chat_history[user] + [user_input])[-8:]
        
        # Concatena o histórico no formato de mensagens para o modelo
        history_text = "\n".join([f"{user}: {msg}" for msg in self.chat_history[user]])
        
        # Template do prompt com o histórico

        ai_msg = self.chain(history_text).invoke({'chat_user': user, 'input': user_input})
        
        # Adiciona a resposta do bot ao histórico do usuário
        self.chat_history[user].append(ai_msg.content)
        
        # Envia a resposta para o chat
        await message.channel.send(f"{ai_msg.content}")
        
        print(user_input, ai_msg.content)

        # Handle commands as usual
        await self.handle_commands(message)
    
    @commands.command()
    async def self_ignore(self, ctx: commands.Context):
        if ctx.author.name == self.nick:
            self.self_ignore = not self.self_ignore
            await ctx.send(f'Self ignore is now {self.self_ignore}')

    @commands.command()
    async def clear_history(self, ctx: commands.Context):
        if ctx.author.name == self.nick:
            
            total_chat_size = sum(len(v) for v in self.chat_history.values())    
            self.chat_history = {}
            await ctx.send('Chat history cleared; total chat size was: ' + str(total_chat_size))
         

bot = Bot(token, llm)
bot.run()
