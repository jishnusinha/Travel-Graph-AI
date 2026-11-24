import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { terraApi } from '@/lib/terra'

export default function SavedPage() {
  const qc = useQueryClient()
  const saved = useQuery({ queryKey: ['terra-saved'], queryFn: terraApi.saved })
  const remove = useMutation({
    mutationFn: (id: string) => terraApi.unsave(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['terra-saved'] }),
  })
  const items = saved.data?.items ?? []
  return (
    <div className="terra-scope -mx-4 -mt-5 px-4 py-6 lg:-mx-6 lg:px-6">
      <div className="mx-auto max-w-3xl">
        <h1 className="terra-serif text-4xl">Saved places</h1>
        {!items.length && <p className="mt-4 text-sm text-muted">Nothing saved yet. Saves stay on your account.</p>}
        <ul className="mt-5 space-y-3">
          {items.map((item) => (
            <li key={String(item.id)} className="flex items-center justify-between rounded-3xl border border-line bg-white px-4 py-3">
              <div>
                <Link className="terra-serif text-2xl" to={`/destinations/${item.slug}`}>{item.name}</Link>
                <p className="text-xs text-muted">{item.region} · {item.source_status}</p>
              </div>
              <button type="button" className="text-sm underline" onClick={() => remove.mutate(String(item.id))}>Remove</button>
            </li>
          ))}
        </ul>
      </div>
    </div>
  )
}
