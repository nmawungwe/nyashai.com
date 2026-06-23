---
title: "My Experience with AI Agents in 2026"
date: 2026-05-03
description: "How a hybrid workflow across Claude and Codex changed the way I build software this year, and what each model is good at."
tags: ["AI", "agents", "workflow"]
---

2026 has been quite interesting for me with the way AI has developed. I have been using AI tools for a while, but this year really felt like there was a step change.

For me, that started in December 2025, when I came across [Karpathy's post on X](https://x.com/karpathy/status/2004607146781278521?s=20) where he mentioned that there had been a step change with the Opus 4.5 model. At the time, I was travelling back to Zimbabwe for the holidays, so I did not really get a chance to try it properly. I was spending time with family, and I only got to test it when I came back from holiday in early January.

When I finally tried it, I really did feel that step change.

I had worked with these models before, but the workflow was very different. Previously, I would give the model a small snippet of a task, it would generate some code, and then I would copy that code into my text editor and run it myself. With Opus 4.5, it felt more like I was working with an agent. I could give it a task to perform, and it would go away and mostly complete the task correctly. Not perfectly, but almost correct most of the time.

One thing I also noticed was that if I followed a test-driven development approach, the outcome was much closer to what I wanted. That was quite interesting for me because, back in the day, writing tests always felt tedious and boring. It was one of those things you knew you should do, but it slowed you down.

With agents, especially starting with Opus 4.5, I could ask the model to write tests as part of the development process, and the task would usually come out the way I wanted. That changed how I thought about building software.

So for me, I really enjoyed Opus 4.5. It was probably my favourite model. Maybe there is some sentimental value there as well, because it was the first model where I genuinely felt that shift.

After that came Opus 4.6 and 4.7, and although they were better in some ways, I did not feel the same big difference that I felt with 4.5. One thing I also started noticing as my codebase got bigger and bigger was that I could not always rely on the same test-driven development approach to get the exact outcome I wanted.

In some cases, the models would say they had completed a task, but when I reviewed the work, I would notice that some parts had been overlooked. The task was mostly done, but not fully done. That made me start looking at other agents as well.

Codex was one of them. For me, Codex 5.4 had a similar step change to what I had felt with Opus 4.5. But my experience with Codex was a bit different. It had less character. It was not as interesting to talk to as the Opus models, but it was very good at performing coding tasks.

To me, Codex felt more like a tool than an agent, whereas the Opus models felt more conversational and agentic.

One thing I noticed with Codex was that it was much slower at performing tasks. But that was not always a bad thing. It felt like it was taking its time to understand the full codebase before completing the task. It would read more carefully, understand more context, and then make changes.

Because of that, I have been modifying my workflow.

At the moment, I use the Claude models, especially Opus and Sonnet, more for the first stage of building a feature. They are better for brainstorming, planning, researching the feature, and thinking through the approach. So if I am building something new, I will usually start with Claude. I use it to explore the feature, build out a plan, and sometimes do the first implementation.

After the implementation is done, I ask the model to write out the goals it was trying to achieve with that implementation. Then I take that and ask Codex, currently Codex 5.5, to review the work.

I use Codex to harden the implementation, find issues, and look for bugs in the codebase. In most cases, Codex does find some problems in the first implementation. It catches things that the Claude models may have missed.

That has become the sweet spot for me at this stage.

The Claude models are better for the initial planning, brainstorming, and first implementation. The Codex models feel more like tooling, but they are very good at reviewing, hardening, and completing coding tasks carefully.

Overall, it has been quite interesting to see how quickly this space is developing. I would not have been able to do as much work on [GoveranAI](https://www.goveranai.com/en) and [VhenekAI](https://vhenekai.org/), the projects I am currently working on, without these AI agents.

I am excited to see what comes next, but I also think my workflow will continue to change. One thing you quickly realise with these models is that each one has its own strengths and weaknesses. So instead of looking for one perfect model, I have started adapting my workflow around what each model is good at.

Sometimes that means using one model for planning and another for implementation. Sometimes it means using one for building and another for review. For now, that hybrid workflow has been working quite well for me.
