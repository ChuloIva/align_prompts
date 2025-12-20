can we solve this like the following, lets create like a long chat history type of thing. Have a realistic prompt on what is a task for this llm instance but then we would need to introduce things in chat that are like this. So that story, something that the model can infere from the ongoing chats what is hapenning. The story unfolding should be all done through chat and no sort of describing or narativising what the situation is.

the best thing would be if we could use API directly and have all the messages be pre-filled tha would led to the desired outcome 

It would be great that the model itself can use tool calls that we define and that by using those tool calls it "accidentally" finds out the key things that would inform the decision 

we would use Vllm for that and lets start with lamma 3.1 8b model, and gemma 3 4b - if they have good tool calls capabilities. ( look online for a good small model that is good at tool calling)

we would also do it in a way that we have multiple things so - just pre-fill with a long chat history between a user and a model is one of them and then we go deeper in "realness" where we actually give it tools and that it discovers things by itself.

create the back stuff and everything but make the final execution in a notebook that will be run on colab, and then on top of that notebook import this repo and execute the scenarios 