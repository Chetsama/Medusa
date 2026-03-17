
I don't think the current integration is working properly, I don't think the routing for the langgraph agents is properly implemented, I think that the requests are being proxied directly to vLLM through the gateway/fastapi_router.py. Can you fix this? Please don't delete the gateway/fastapi_router.py

As I understand it, the way the routing is currently happening, a request is sent to http://localhost:9000 and this is then proxied through the fastapi_router to vLLM. I would like the routing to look like this instead

http://localhost:9000 -> fastapi_router.py -> langgraph -> vLLM

Can you adjust the endpoints in docker-compose and any other appropriate files to ensure this is working? 



Favour editing existing files over creating new ones. Don't attempt to run the project.
