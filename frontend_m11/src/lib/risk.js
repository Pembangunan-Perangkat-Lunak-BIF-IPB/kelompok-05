export const pick=(o,...ks)=>{for(const k of ks)if(o?.[k]!=null)return o[k];return null}
const num=x=>x==null||x===''||!Number.isFinite(Number(x))?null:Number(x)
export const SORTS={pos_asc:'Posisi (naik)',pos_desc:'Posisi (turun)',qual_desc:'QUAL (tertinggi)',dp_desc:'DP (tertinggi)'}
export function readMetrics(data){
const m=data?.summary_metrics??data?.metrics??data?.run_metrics??data?.summary??{}
return {
q20:pick(m,'q20_rate','q20','q20_percent'),q30:pick(m,'q30_rate','q30','q30_percent'),
mapping:pick(m,'mapping_rate'),depth:pick(m,'mean_depth'),
raw:pick(m,'raw_variant_count'),passed:pick(m,'passed_variant_count'),
filtered:pick(m,'filtered_variant_count'),annotated:pick(m,'annotated_variant_count'),
annotation_status:pick(m,'annotation_status')??data?.annotation_status,
total:pick(m,'total_variants','variant_count')??data?.total_variants,
tstv:pick(m,'tstv_ratio','ts_tv_ratio','ts_tv')}
}

export function normalizeVariants(data) {
  const list = data?.variants ?? data?.variant_results ?? []

  if (!Array.isArray(list)) return []

  return list.map((v) => ({
    ...v,

    // Menyesuaikan nama field backend dengan frontend
    position: v.position ?? v.pos ?? null,
    ref_allele: v.ref_allele ?? v.ref ?? null,
    alt_allele: v.alt_allele ?? v.alt ?? null,

    // Informasi anotasi SnpEff
    gene: v.gene ?? v.gene_name ?? null,
    impact: v.impact ?? v.snpeff_impact ?? null,
  }))
}
export function sortVariants(list,key='pos_asc'){
const pos=(a,b)=>(num(a.position)??0)-(num(b.position)??0)
return [...list].sort(({pos_asc:pos,pos_desc:(a,b)=>pos(b,a),
qual_desc:(a,b)=>(num(b.qual)??-Infinity)-(num(a.qual)??-Infinity)||pos(a,b),
dp_desc:(a,b)=>(num(b.dp)??-Infinity)-(num(a.dp)??-Infinity)||pos(a,b)})[key]??pos)
}
export function filterVariants(list,{impact='ALL',effect=''}={}){
const q=String(effect).trim().toLowerCase()
return list.filter(v=>(impact==='ALL'||String(v.impact??'').toUpperCase()===impact)&&(!q||[v.position,v.gene,v.snpeff_effect,v.hgvs_c,v.hgvs_p].some(x=>String(x??'').toLowerCase().includes(q))))
}
const csvCell=v=>{const s=v==null?'':String(v);const t=/^[=+@\-\t\r]/.test(s)?"'"+s:s;return /[",\n]/.test(t)?`"${t.replace(/"/g,'""')}"`:t}
export function toCsv(list){const keys=['position','ref_allele','alt_allele','gene','qual','dp','af','snpeff_effect','impact','hgvs_c','hgvs_p'];return [keys.join(','),...list.map(v=>keys.map(k=>csvCell(v[k])).join(','))].join('\r\n')}
export function downloadText(filename,contents,mime='text/csv'){const url=URL.createObjectURL(new Blob([contents],{type:mime}));const a=document.createElement('a');a.href=url;a.download=filename;document.body.appendChild(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),1000)}
