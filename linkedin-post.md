I built an AI fact-checker for TikTok and Instagram Reels. It's called Veritas, it's free, and you can try it right now.

Most fact-checking tools are built for text articles and tweets. Short-form video, the format that actually dominates how my generation gets news, has almost nothing. A creator can say whatever they want over stock footage, and by the time a journalist writes a debunk three days later, the clip has 2 million views.

Veritas takes a TikTok link and returns a sourced verdict in about 2 minutes. It downloads the video, transcribes the audio, reads on-screen text, runs a reverse image search to catch recycled footage, pulls real sources from the web, then has Claude AI analyze every claim with citations. You see exactly why something checks out or doesn't.

The whole stack runs on free tiers (Render, Vercel, MongoDB Atlas). Total cost: $0/month. Making the pipeline fast enough on zero budget was the real engineering challenge. I started at 10-minute scans and got it down to about 2 minutes by running tasks in parallel, capping audio processing, and combining multiple AI calls into one.

This is a solo student project and it's not perfect. Free speech-to-text chokes on background music, YouTube blocks downloads from cloud servers half the time, and AI still makes mistakes. But it works, it's live, and I think it shows that automated video fact-checking is feasible even with no budget.

Try it: project-veritas-mauve.vercel.app
Demo: [ADD YOUR GOOGLE DRIVE LINK HERE]
Code: github.com/Vystanley/project-veritas

#factchecking #ai #misinformation #studentproject
