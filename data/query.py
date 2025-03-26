MATCHED_VOLUME_QUERY = """
  select m.datetime, m.price, v.quantity
  from quote.matched m join quote.matchedvolume v on m.datetime = v.datetime and m.tickersymbol = v.tickersymbol
  join quote.futurecontractcode fc on date(m.datetime) = fc.datetime and fc.tickersymbol = m.tickersymbol
  where fc.futurecode = 'VN30F1M'
    and m.datetime between %s and %s
    and (
        m.datetime::TIME BETWEEN '09:15:00' AND '11:30:00'
        OR m.datetime::TIME BETWEEN '13:00:00' AND '14:30:00'
    )
  order by m.datetime
"""