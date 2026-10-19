import math, re, time

def compute(kind, payload):
    if kind == 'prime':
        n = int(payload.get('limit', 10000))
        if not 2 <= n <= 250000: raise ValueError('limit must be 2..250000')
        primes = []
        for i in range(2, n+1):
            if all(i % j for j in range(2, math.isqrt(i)+1)): primes.append(i)
        return {'count':len(primes),'last_ten':primes[-10:]}
    if kind == 'fibonacci':
        n=int(payload.get('count', 25))
        if not 1 <= n <= 300: raise ValueError('count must be 1..300')
        a,b=0,1; result=[]
        for _ in range(n): result.append(str(a));a,b=b,a+b
        return {'sequence':result[:35], 'last':str(result[-1]), 'total_terms':n}
    if kind == 'statistics':
        values=payload.get('values', [3,5,8,13,21])
        if not isinstance(values,list) or not 1 <= len(values) <= 10000: raise ValueError('values must be a nonempty list up to 10000')
        values=[float(v) for v in values]
        if not all(math.isfinite(v) for v in values): raise ValueError('values must be finite')
        return {'sum':sum(values),'average':sum(values)/len(values),'min':min(values),'max':max(values),'count':len(values)}
    if kind == 'wordcount':
        content=str(payload.get('text','Distributed systems make computing resilient'))
        if len(content)>20000: raise ValueError('text too long')
        words=re.findall(r"[a-z0-9']+",content.lower()); counts={}
        for word in words: counts[word]=counts.get(word,0)+1
        return {'total':len(words),'unique':len(counts),'frequencies':dict(sorted(counts.items(),key=lambda x:(-x[1],x[0]))[:30])}
    if kind == 'benchmark':
        seconds=float(payload.get('seconds',3))
        if not 0.2 <= seconds <= 15: raise ValueError('seconds must be 0.2..15')
        start=time.monotonic(); count=0
        while time.monotonic()-start < seconds: count+=1; math.sqrt(count % 99991)
        return {'iterations':count,'duration_seconds':round(time.monotonic()-start,2)}
    raise ValueError('Unknown task type')
