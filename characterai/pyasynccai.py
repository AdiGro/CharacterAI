from contextlib import asynccontextmanager
import websockets
import tls_client
import asyncio
import json
import logging

from characterai import errors

_log = logging.getLogger(__name__)

__all__ = ['PyCAI', 'PyAsyncCAI']

class PyAsyncCAI:
    def __init__(
        self, token: str = None, plus: bool = False
    ):
        _log.debug("Initializing PyAsyncCAI")
        self.token = token

        sub = 'plus' if plus else 'beta'
        self.session = tls_client.Session(
            client_identifier='chrome112'
        )

        setattr(self.session, 'url', f'https://{sub}.character.ai/')
        setattr(self.session, 'token', token)

        self.user = self.user(token, self.session)
        self.post = self.post(token, self.session)
        self.character = self.character(token, self.session)
        self.chat = self.chat(token, self.session)
        self.chat2 = self.chat2(token, None, self.session)

    async def request(
        url: str, session: tls_client.Session,
        *, token: str = None, method: str = 'GET',
        data: dict = None, split: bool = False,
        neo: bool = False
    ):
        _log.debug(f"Making request to URL: {url} with method: {method}")
        if neo:
            link = f'https://neo.character.ai/{url}'
        else:
            link = f'{session.url}{url}'

        if token == None:
            key = session.token
        else:
            key = token

        headers = {
            'Authorization': f'Token {key}'
        }

        if method == 'GET':
            response = session.get(
                link, headers=headers
            )

        elif method == 'POST':
            response = session.post(
                link, headers=headers, json=data
            )

        elif method == 'PUT':
            response = session.put(
                link, headers=headers, json=data
            )

        _log.debug(f"Received response: {response}. Status code: {response.status_code}")
        _log.debug(f"Response text: {response.text}")


        if split:
            data = json.loads(response.text.split('\n')[-2])
        else:
            data = response.json()

        if str(data).startswith("{'command': 'neo_error'"):
            raise errors.ServerError(data['comment'])
        elif str(data).startswith("{'detail': 'Auth"):
            raise errors.AuthError('Invalid token')
        elif str(data).startswith("{'status': 'Error"):
            raise errors.ServerError(data['status'])
        elif str(data).startswith("{'error'"):
            raise errors.ServerError(data['error'])
        else:
            return data

    async def ping(self):
        _log.debug("Pinging server")
        return self.session.get(
            'https://neo.character.ai/ping/'
        ).json()

    @asynccontextmanager
    async def connect(self, token: str = None):
        _log.debug("Connecting to server")
        try:
            if token == None: key = self.token
            else: key = token

            setattr(self.session, 'token', key)

            try:
                self.ws = await websockets.connect(
                    'wss://neo.character.ai/ws/',
                    extra_headers={'Cookie': f'HTTP_AUTHORIZATION="Token {key}"'}
                )
            except websockets.exceptions.InvalidStatusCode:
                raise errors.AuthError('Invalid token')
            
            yield PyAsyncCAI.chat2(key, self.ws, self.session)
        finally:
            _log.debug("Closing connection")
            await self.ws.close()

    class user:
        """Responses from site for user info

        user.info()
        user.get_profile('USERNAME')
        user.followers()
        user.following()
        user.update('USERNAME')

        """
        def __init__(
            self, token: str, session: tls_client.Session
        ):
            self.token = token
            self.session = session
            _log.debug("User object initialized")

        async def info(self, *, token: str = None):
            _log.debug("Getting user info")
            return await PyAsyncCAI.request(
                'chat/user/', self.session, token=token
            )

        async def get_profile(
            self, username: str, *,
            token: str = None
        ):
            _log.debug(f"Getting profile for username: {username}")
            return await PyAsyncCAI.request(
                'chat/user/public/', self.session,
                token=token, method='POST',
                data={
                    'username': username
                }
            )

        async def followers(self, *, token: str = None):
            _log.debug("Getting followers")
            return await PyAsyncCAI.request(
                'chat/user/followers/', self.session, token=token
            )

        async def following(self, *, token: str = None):
            _log.debug("Getting following")
            return await PyAsyncCAI.request(
                'chat/user/following/', self.session, token=token
            )
        
        async def recent(self, *, token: str = None):
            _log.debug("Getting recent characters")
            return await PyAsyncCAI.request(
                'chat/characters/recent/', self.session, token=token
            )

        async def characters(self, *, token: str = None):
            _log.debug("Getting characters")
            return await PyAsyncCAI.request(
                'chat/characters/?scope=user',
                self.session, token=token
            )

        async def update(
            self, username: str,
            *, token: str = None,
            **kwargs
        ):
            _log.debug(f"Updating user with username: {username}, additional data: {kwargs}")
            return await PyAsyncCAI.request(
                'chat/user/update/', self.session,
                token=token, method='POST',
                data={
                    'username': username,
                    **kwargs
                }
            )
    class post:
        """Just a responses from site for posts
        
        post.get_post('POST_ID')
        post.my_posts()
        post.get_posts('USERNAME')
        post.upvote('POST_ID')
        post.undo_upvote('POST_ID')
        post.send_comment('POST_ID', 'TEXT')
        post.delete_comment('MESSAGE_ID', 'POST_ID')
        post.create('HISTORY_ID', 'TITLE')
        post.delete('POST_ID')

        """
        def __init__(
            self, token: str, session: tls_client.Session
        ):
            self.token = token
            self.session = session
            _log.debug("Post object initialized")

        async def get_post(
            self, post_id: str
        ):
            _log.debug(f"Getting post with ID: {post_id}")
            return await PyAsyncCAI.request(
                f'chat/post/?post={post_id}',
                self.session
            )

        async def my(
            self, *, posts_page: int = 1,
            posts_to_load: int = 5, token: str = None
        ):
            _log.debug(f"Getting my posts, page: {posts_page}, posts to load: {posts_to_load}")
            return await PyAsyncCAI.request(
                f'chat/posts/user/?scope=user&page={posts_page}'
                f'&posts_to_load={posts_to_load}/',
                self.session
            )

        async def get_posts(
            self, username: str, *,
            posts_page: int = 1, posts_to_load: int = 5,
        ):
            _log.debug(f"Getting posts for username: {username}, page: {posts_page}, posts to load: {posts_to_load}")
            return await PyAsyncCAI.request(
                f'chat/posts/user/?username={username}'
                f'&page={posts_page}&posts_to_load={posts_to_load}/',
                self.session
            )

        async def upvote(
            self, post_external_id: str,
            *, token: str = None
        ):
            _log.debug(f"Upvoting post with external ID: {post_external_id}")
            return await PyAsyncCAI.request(
                'chat/post/upvote/', self.session,
                token=token, method='POST',
                data={
                    'post_external_id': post_external_id
                }
            )

        async def undo_upvote(
            self, post_external_id: str,
            *, token: str = None
        ):
            _log.debug(f"Undoing upvote for post with external ID: {post_external_id}")
            return await PyAsyncCAI.request(
                'chat/post/undo-upvote/', self.session,
                token=token, method='POST',
                data={
                    'post_external_id': post_external_id
                }
            )

        async def send_comment(
            self, post_id: str, text: str, *,
            parent_uuid: str = None, token: str = None
        ):
            _log.debug(f"Sending comment to post with ID: {post_id}, text: {text}, parent UUID: {parent_uuid}")
            return await PyAsyncCAI.request(
                'chat/comment/create/', self.session,
                token=token, method='POST',
                data={
                    'post_external_id': post_id,
                    'text': text,
                    'parent_uuid': parent_uuid
                }
            )

        async def delete_comment(
            self, message_id: int, post_id: str,
            *, token: str = None
        ):
            _log.debug(f"Deleting comment with message ID: {message_id} from post with ID: {post_id}")
            return await PyAsyncCAI.request(
                'chat/comment/delete/', self.session,
                token=token, method='POST',
                data={
                    'external_id': message_id,
                    'post_external_id': post_id
                }
            )

        async def create(
            self, post_type: str, external_id: str,
            title: str, text: str = '',
            post_visibility: str = 'PUBLIC',
            token: str = None, **kwargs
        ):
            _log.debug(f"Creating post with type: {post_type}, external ID: {external_id}, title: {title}, text: {text}, visibility: {post_visibility}, additional data: {kwargs}")
            if post_type == 'POST':
                post_link = 'chat/post/create/'
                data = {
                    'post_title': title,
                    'topic_external_id': external_id,
                    'post_text': text,
                    **kwargs
                }
            elif post_type == 'CHAT':
                post_link = 'chat/chat-post/create/'
                data = {
                    'post_title': title,
                    'subject_external_id': external_id,
                    'post_visibility': post_visibility,
                    **kwargs
                }
            else:
                raise errors.PostTypeError('Invalid post_type')

            return await PyAsyncCAI.request(
                post_link, self.session,
                token=token, method='POST'
            )

        async def delete(
            self, post_id: str, *,
            token: str = None
        ):
            _log.debug(f"Deleting post with ID: {post_id}")
            return await PyAsyncCAI.request(
                'chat/post/delete/', self.session,
                token=token, method='POST',
                data={
                    'external_id': post_id
                }
            )

        async def get_topics(self):
            _log.debug("Getting topics")
            return await PyAsyncCAI.request(
                'chat/topics/', self.session
            )

        async def feed(
            self, topic: str, num: int = 1, 
            load: int = 5, sort: str = 'top', *,
            token: str = None
        ):
            _log.debug(f"Getting feed for topic: {topic}, page: {num}, posts to load: {load}, sort: {sort}")
            return await PyAsyncCAI.request(
                f'chat/posts/?topic={topic}&page={num}'
                f'&posts_to_load={load}&sort={sort}',
                self.session, token=token
            )

    class character:
        """Just a responses from site for characters

        character.create()
        character.update()
        character.trending()
        character.recommended()
        character.categories()
        character.info('CHAR')
        character.search('QUERY')
        character.voices()

        """
        def __init__(
            self, token: str, session: tls_client.Session
        ):
            self.token = token
            self.session = session
            _log.debug("Character object initialized")

        async def create(
            self, greeting: str, identifier: str,
            name: str, *, avatar_rel_path: str = '',
            base_img_prompt: str = '', categories: list = [],
            copyable: bool = True, definition: str = '',
            description: str = '', title: str = '',
            img_gen_enabled: bool = False,
            visibility: str = 'PUBLIC',
            token: str = None, **kwargs
        ):
            _log.debug(f"Creating character with greeting: {greeting}, identifier: {identifier}, name: {name}, title: {title}, visibility: {visibility}, additional data: {kwargs}")
            return await PyAsyncCAI.request(
                '../chat/character/create/', self.session,
                token=token, method='POST',
                data={
                    'greeting': greeting,
                    'identifier': identifier,
                    'name': name,
                    'avatar_rel_path': avatar_rel_path,
                    'base_img_prompt': base_img_prompt,
                    'categories': categories,
                    'copyable': copyable,
                    'definition': definition,
                    'description': description,
                    'img_gen_enabled': img_gen_enabled,
                    'title': title,
                    'visibility': visibility,
                    **kwargs
                }
            )

        async def update(
            self, external_id: str, greeting: str,
            identifier: str, name: str, title: str = '',
            categories: list = [], definition: str = '',
            copyable: bool = True, description: str = '',
            visibility: str = 'PUBLIC', *,
            token: str = None, **kwargs
        ):
            _log.debug(f"Updating character with external ID: {external_id}, greeting: {greeting}, identifier: {identifier}, name: {name}, title: {title}, visibility: {visibility}, additional data: {kwargs}")
            return await PyAsyncCAI.request(
                '../chat/character/update/', self.session,
                token=token, method='POST',
                data={
                    'external_id': external_id,
                    'name': name,
                    'categories': categories,
                    'title': title,
                    'visibility': visibility,
                    'copyable': copyable,
                    'description': description,
                    'greeting': greeting,
                    'definition': definition,
                    **kwargs
                }
            )

        async def trending(self):
            _log.debug("Getting trending characters")
            return await PyAsyncCAI.request(
                'chat/characters/trending/',
                self.session
            )

        async def recommended(
            self, *, token: str = None
        ):
            _log.debug("Getting recommended characters")
            return await PyAsyncCAI.request(
                'chat/characters/recommended/',
                self.session, token=token
            )

        async def categories(self):
            _log.debug("Getting character categories")
            return await PyAsyncCAI.request(
                'chat/character/categories/',
                self.session
            )

        async def info(
            self, char: str, *,
            token: str = None,
        ):
            _log.debug(f"Getting info for character: {char}")
            return await PyAsyncCAI.request(
                'chat/character/', self.session,
                token=token, method='POST',
                data={
                    'external_id': char
                }
            )

        async def search(
            self, query: str, *,
            token: str = None
        ):
            _log.debug(f"Searching characters with query: {query}")
            return await PyAsyncCAI.request(
                f'chat/characters/search/?query={query}/',
                self.session, token=token
            )

        async def voices(self):
            _log.debug("Getting character voices")
            return await PyAsyncCAI.request(
                'chat/character/voices/',
                self.session
            )

    class chat:
        """Managing a chat with a character

        chat.create_room('CHARACTERS', 'NAME', 'TOPIC')
        chat.rate(NUM, 'HISTORY_ID', 'MESSAGE_ID')
        chat.next_message('CHAR', 'MESSAGE')
        chat.get_histories('CHAR')
        chat.get_history('HISTORY_EXTERNAL_ID')
        chat.get_chat('CHAR')
        chat.send_message('CHAR', 'MESSAGE')
        chat.delete_message('HISTORY_ID', 'UUIDS_TO_DELETE')
        chat.new_chat('CHAR')

        """
        def __init__(
            self, token: str, session: tls_client.Session
        ):
            self.token = token
            self.session = session
            _log.debug("Chat object initialized")

        async def create_room(
            self, characters: list, name: str,
            topic: str = '', *, token: str = None,
            **kwargs
        ):
            _log.debug(f"Creating room with characters: {characters}, name: {name}, topic: {topic}, additional data: {kwargs}")
            return await PyAsyncCAI.request(
                '../chat/room/create/', self.session,
                token=token, method='POST',
                data={
                    'characters': characters,
                    'name': name,
                    'topic': topic,
                    'visibility': 'PRIVATE',
                    **kwargs
                }
            )

        async def rate(
            self, rate: int, history_id: str,
            message_id: str, *, token: str = None,
            **kwargs
        ):
            _log.debug(f"Rating with rate: {rate}, history_id: {history_id}, message_id: {message_id}, additional data: {kwargs}")
            if rate == 0: label = [234, 238, 241, 244] #Terrible
            elif rate == 1: label = [235, 237, 241, 244] #Bad
            elif rate == 2: label = [235, 238, 240, 244] #Good
            elif rate == 3: label = [235, 238, 241, 243] #Fantastic
            else: raise errors.LabelError('Wrong Rate Value')

            return await PyAsyncCAI.request(
                'chat/annotations/label/', self.session,
                token=token, method='PUT',
                data={
                    'label_ids': label,
                    'history_external_id': history_id,
                    'message_uuid': message_id,
                    **kwargs
                }
            )

        async def next_message(
            self, history_id: str, parent_msg_uuid: str,
            tgt: str, *, token: str = None, **kwargs
        ):
            _log.debug(f"Getting next message for history_id: {history_id}, parent_msg_uuid: {parent_msg_uuid}, tgt: {tgt}, additional data: {kwargs}")
            response = await PyAsyncCAI.request(
                'chat/streaming/', self.session,
                token=token, method='POST', split=True,
                data={
                    'history_external_id': history_id,
                    'parent_msg_uuid': parent_msg_uuid,
                    'tgt': tgt,
                    **kwargs
                }
            )

        async def get_histories(
            self, char: str, *, number: int = 50,
            token: str = None
        ):
            _log.debug(f"Getting histories for character: {char}, number: {number}")
            return await PyAsyncCAI.request(
                'chat/character/histories_v2/', self.session,
                token=token, method='POST',
                data={'external_id': char, 'number': number},
            )

        async def get_history(
            self, history_id: str = None,
            *, token: str = None
        ):
            _log.debug(f"Getting history for history_id: {history_id}")
            return await PyAsyncCAI.request(
                'chat/history/msgs/user/?'
                f'history_external_id={history_id}',
                self.session, token=token
            )

        async def get_chat(
            self, char: str = None, *,
            token: str = None
        ):
            _log.debug(f"Getting chat for character: {char}")
            return await PyAsyncCAI.request(
                'chat/history/continue/', self.session,
                token=token, method='POST',
                data={
                    'character_external_id': char
                }
            )

        async def send_message(
            self, history_id: str, tgt: str, text: str,
            *, token: str = None, **kwargs
        ):
            _log.debug(f"Sending message with history_id: {history_id}, tgt: {tgt}, text: {text}, additional data: {kwargs}")
            return await PyAsyncCAI.request(
                'chat/streaming/', self.session,
                token=token, method='POST', split=True,
                data={
                    'history_external_id': history_id,
                    'tgt': tgt,
                    'text': text,
                    **kwargs
                }
            )

        async def delete_message(
            self, history_id: str, uuids_to_delete: list,
            *, token: str = None, **kwargs
        ):
            _log.debug(f"Deleting message with history_id: {history_id}, uuids_to_delete: {uuids_to_delete}, additional data: {kwargs}")
            return await PyAsyncCAI.request(
                'chat/history/msgs/delete/', self.session,
                token=token, method='POST',
                data={
                    'history_id': history_id,
                    'uuids_to_delete': uuids_to_delete,
                    **kwargs
                }
            )
        async def new_chat(
            self, char: str, *, token: str = None
        ):
            _log.debug(f"Creating new chat for character: {char}")
            return await PyAsyncCAI.request(
                'chat/history/create/', self.session,
                token=token, method='POST',
                data={
                    'character_external_id': char
                }
            )

    class chat2:
        """Managing a chat2 with a character

        chat.next_message('CHAR', 'CHAT_ID', 'PARENT_ID')
        chat.send_message('CHAR', 'CHAT_ID', 'TEXT', {AUTHOR})
        chat.next_message('CHAR', 'MESSAGE')
        chat.new_chat('CHAR', 'CHAT_ID', 'CREATOR_ID')
        chat.get_histories('CHAR')
        chat.get_chat('CHAR')
        chat.get_history('CHAT_ID')
        chat.rate(RATE, 'CHAT_ID', 'TURN_ID', 'CANDIDATE_ID')
        chat.delete_message('CHAT_ID', 'TURN_ID')

        """
        def __init__(
            self, token: str,
            ws: websockets.WebSocketClientProtocol,
            session: tls_client.Session
        ):
            self.token = token
            self.session = session
            self.ws = ws

        async def next_message(
            self, char: str, chat_id: str,
            parent_msg_uuid: str
        ):
            _log.debug(f"Sending next message request for character: {char}, chat_id: {chat_id}, parent_msg_uuid: {parent_msg_uuid}")
            await self.ws.send(json.dumps({
                'command': 'generate_turn_candidate',
                'payload': {
                    'character_id': char,
                    'turn_key': {
                        'turn_id': parent_msg_uuid,
                        'chat_id': chat_id
                    }
                }
            }))

            while True:
                response = json.loads(await self.ws.recv())
                try: response['turn']
                except: raise errors.ServerError(response['comment'])
                
                if not response['turn']['author']['author_id'].isdigit():
                    try: is_final = response['turn']['candidates'][0]['is_final']
                    except: pass
                    else:
                        _log.debug(f"Received next message response: {response}")
                        return response

        async def send_message(
            self, char: str, chat_id: str,
            text: str, author: dict = None,
            *, turn_id: str = None, custom_id: str = None,
            candidate_id: str = None
        ):  
            _log.debug(f"Sending message for character: {char}, chat_id: {chat_id}, text: {text}")
            
            if custom_id != None:
                turn_key = {
                    'turn_id': custom_id,
                    'chat_id': chat_id
                }
            else:
                turn_key = {'chat_id': chat_id}
            
            message = {
                'command': 'create_and_generate_turn',
                'payload': {
                    'character_id': char,
                    'turn': {
                        'turn_key': turn_key,
                        'author': author,
                        'candidates': [{'raw_content': text}]
                    }
                }
            }

            if turn_id != None and candidate_id != None:
                message['update_primary_candidate'] = {
                    'candidate_id': candidate_id,
                    'turn_key': {
                        'turn_id': turn_id,
                        'chat_id': chat_id
                    }
                }
        
            await self.ws.send(json.dumps(message))

            while True:
                response = json.loads(await self.ws.recv())

                try: response['turn']
                except: raise errors.ServerError(response['comment'])
                
                if not response['turn']['author']['author_id'].isdigit():
                    try: is_final = response['turn']['candidates'][0]['is_final']
                    except: pass
                    else: 
                        _log.debug(f"Received message response: {response}")
                        return response

        async def new_chat(
            self, char: str, chat_id: str,
            creator_id: str, *, with_greeting: bool = True
        ):
            _log.debug(f"Creating new chat for character: {char}, chat_id: {chat_id}, creator_id: {creator_id}")
            
            await self.ws.send(json.dumps({
                'command': 'create_chat',
                'payload': {
                    'chat': {
                        'chat_id': chat_id,
                        'creator_id': creator_id,
                        'visibility': 'VISIBILITY_PRIVATE',
                        'character_id': char,
                        'type': 'TYPE_ONE_ON_ONE'
                    },
                    'with_greeting': with_greeting
                }
            }))

            response = json.loads(await self.ws.recv())
            try: response['chat']
            except KeyError:
                raise errors.ServerError(response['comment'])
            else:
                answer = json.loads(await self.ws.recv())
                _log.debug(f"Received new chat response: {response}, answer: {answer}")
                return response, answer

        async def get_histories(
            self, char: str = None, *,
            preview: int = 2, token: str = None
        ):
            _log.debug(f"Getting histories for character: {char}, preview: {preview}")
            return await PyAsyncCAI.request(
                f'chats/?character_ids={char}'
                f'&num_preview_turns={preview}',
                self.session, token=token, neo=True
            )

        async def get_chat(
            self, char: str = None, *,
            token: str = None
        ):
            _log.debug(f"Getting chat for character: {char}")
            return await PyAsyncCAI.request(
                f'chats/recent/{char}',
                self.session, token=token, neo=True
            )

        async def get_history(
            self, chat_id: str = None, *,
            token: str = None
        ):
            _log.debug(f"Getting history for chat_id: {chat_id}")
            return await PyAsyncCAI.request(
                f'turns/{chat_id}/', self.session,
                token=token, neo=True
            )

        async def rate(
            self, rate: int, chat_id: str,
            turn_id: str, candidate_id: str,
            *, token: str = None
        ):
            _log.debug(f"Rating chat: {chat_id}, turn: {turn_id}, candidate: {candidate_id} with rate: {rate}")
            return await PyAsyncCAI.request(
                'annotation/create', self.session,
                token=token, method='POST', neo=True,
                data={
                    'turn_key': {
                        'chat_id': chat_id,
                        'turn_id': turn_id
                    },
                    'candidate_id': candidate_id,
                    'annotation': {
                        'annotation_type': 'star',
                        'annotation_value': rate
                    }
                }
            )

        async def delete_message(
            self, chat_id: str, turn_ids: list,
            *, token: str = None, **kwargs
        ):
            _log.debug(f"Deleting messages in chat: {chat_id}, turns: {turn_ids}")
            await self.ws.send(json.dumps({
                'command':'remove_turns',
                'payload': {
                    'chat_id': chat_id,
                    'turn_ids': turn_ids
                }
            }))
            res = await self.ws.recv()
            _log.debug(f"Received delete message response: {res}")
            return json.loads(res)
