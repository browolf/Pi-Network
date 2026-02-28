"use client"
import { useEffect, useState } from "react"

export default function Home() {
  const [data, setData] = useState<any>(null)

  useEffect(() => {
    fetch("http://localhost:8000/api/prices")
      .then(res => res.json())
      .then(setData)
  }, [])

  if (!data) return <div className="p-10 text-xl">Loading...</div>

  return (
    <div className="min-h-screen bg-gray-950 text-white p-10">
      <h1 className="text-4xl font-bold mb-8">PI Market Intelligence</h1>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {data.prices.map((p:any) => (
          <div key={p.exchange}
            className="bg-gray-800 rounded-2xl p-6 shadow-lg">
            <h2 className="text-xl">{p.exchange}</h2>
            <p className="text-3xl font-bold">${p.price}</p>
            <p className="text-sm text-gray-400">
              Vol: {p.volume}
            </p>
          </div>
        ))}
      </div>

      <div className="mt-10 bg-green-900 p-6 rounded-2xl">
        <h2 className="text-2xl font-bold">Arbitrage</h2>
        <p>Buy: {data.arbitrage?.buy_from}</p>
        <p>Sell: {data.arbitrage?.sell_to}</p>
        <p>Spread: {data.arbitrage?.spread_percent}%</p>
        <p>Profit / 1000 PI: ${data.arbitrage?.potential_profit_per_1000}</p>
      </div>

      <div className="mt-6 bg-blue-900 p-6 rounded-2xl">
        <h2 className="text-xl">AI Signal</h2>
        <p>{data.ai_signal}</p>
      </div>
    </div>
  )
}
