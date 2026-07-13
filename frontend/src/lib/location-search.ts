import "server-only"

import { cityMapping } from "city-timezones"

export type LocationResult = {
  id: string
  name: string
  region: string
  country: string
  latitude: number
  longitude: number
  timezone: string
}

type Locale = "zh" | "en"
type CityRecord = (typeof cityMapping)[number]
type CuratedLocation = LocationResult & {
  nameEn: string
  regionEn: string
  countryEn: string
  aliases: string[]
  population: number
}
type IndexedLocation = {
  resultEn: LocationResult
  resultZh?: LocationResult
  normalizedText: string
  population: number
  curated: boolean
}

export const MAX_QUERY_LENGTH = 80
/** Current-location candidates farther than 120 km are considered unclear. */
export const MAX_NEAREST_DISTANCE_KM = 120

export const CURATED_LOCATIONS: CuratedLocation[] = [
  { id: "CN:beijing", name: "北京", nameEn: "Beijing", region: "北京市", regionEn: "Beijing", country: "中国", countryEn: "China", latitude: 39.92889223, longitude: 116.3882857, timezone: "Asia/Shanghai", aliases: ["北京", "北京市", "beijing"], population: 9293300.5 },
  { id: "CN:shanghai", name: "上海", nameEn: "Shanghai", region: "上海市", regionEn: "Shanghai", country: "中国", countryEn: "China", latitude: 31.21645245, longitude: 121.4365047, timezone: "Asia/Shanghai", aliases: ["上海", "上海市", "shanghai"], population: 14797756 },
  { id: "CN:tianjin", name: "天津", nameEn: "Tianjin", region: "天津市", regionEn: "Tianjin", country: "中国", countryEn: "China", latitude: 39.13002626, longitude: 117.2000191, timezone: "Asia/Shanghai", aliases: ["天津", "天津市", "tianjin"], population: 5473103.5 },
  { id: "CN:chongqing", name: "重庆", nameEn: "Chongqing", region: "重庆市", regionEn: "Chongqing", country: "中国", countryEn: "China", latitude: 29.56497703, longitude: 106.5949816, timezone: "Asia/Shanghai", aliases: ["重庆", "重慶", "重庆市", "chongqing"], population: 5214014 },
  { id: "CN:shijiazhuang", name: "石家庄", nameEn: "Shijiazhuang", region: "河北省", regionEn: "Hebei", country: "中国", countryEn: "China", latitude: 38.05001467, longitude: 114.4799784, timezone: "Asia/Shanghai", aliases: ["石家庄", "石家莊", "shijiazhuang", "shijianzhuang"], population: 2204737 },
  { id: "CN:taiyuan", name: "太原", nameEn: "Taiyuan", region: "山西省", regionEn: "Shanxi", country: "中国", countryEn: "China", latitude: 37.87501243, longitude: 112.5450577, timezone: "Asia/Shanghai", aliases: ["太原", "taiyuan"], population: 2817737.5 },
  { id: "CN:hohhot", name: "呼和浩特", nameEn: "Hohhot", region: "内蒙古自治区", regionEn: "Inner Mongolia", country: "中国", countryEn: "China", latitude: 40.81997479, longitude: 111.6599955, timezone: "Asia/Shanghai", aliases: ["呼和浩特", "hohhot"], population: 1250238.5 },
  { id: "CN:shenyang", name: "沈阳", nameEn: "Shenyang", region: "辽宁省", regionEn: "Liaoning", country: "中国", countryEn: "China", latitude: 41.80497927, longitude: 123.4499735, timezone: "Asia/Shanghai", aliases: ["沈阳", "瀋陽", "shenyang", "shenyeng"], population: 4149596 },
  { id: "CN:changchun", name: "长春", nameEn: "Changchun", region: "吉林省", regionEn: "Jilin", country: "中国", countryEn: "China", latitude: 43.86500856, longitude: 125.3399873, timezone: "Asia/Shanghai", aliases: ["长春", "長春", "changchun"], population: 2860210.5 },
  { id: "CN:harbin", name: "哈尔滨", nameEn: "Harbin", region: "黑龙江省", regionEn: "Heilongjiang", country: "中国", countryEn: "China", latitude: 45.74998395, longitude: 126.6499849, timezone: "Asia/Shanghai", aliases: ["哈尔滨", "哈爾濱", "harbin"], population: 3425441.5 },
  { id: "CN:nanjing", name: "南京", nameEn: "Nanjing", region: "江苏省", regionEn: "Jiangsu", country: "中国", countryEn: "China", latitude: 32.05001914, longitude: 118.7799743, timezone: "Asia/Shanghai", aliases: ["南京", "nanjing"], population: 3383005 },
  { id: "CN:hangzhou", name: "杭州", nameEn: "Hangzhou", region: "浙江省", regionEn: "Zhejiang", country: "中国", countryEn: "China", latitude: 30.24997398, longitude: 120.1700187, timezone: "Asia/Shanghai", aliases: ["杭州", "hangzhou"], population: 2442564.5 },
  { id: "CN:hefei", name: "合肥", nameEn: "Hefei", region: "安徽省", regionEn: "Anhui", country: "中国", countryEn: "China", latitude: 31.85003135, longitude: 117.2800142, timezone: "Asia/Shanghai", aliases: ["合肥", "hefei"], population: 1711952 },
  { id: "CN:fuzhou", name: "福州", nameEn: "Fuzhou", region: "福建省", regionEn: "Fujian", country: "中国", countryEn: "China", latitude: 26.07999595, longitude: 119.3000459, timezone: "Asia/Shanghai", aliases: ["福州", "fuzhou"], population: 1892860 },
  { id: "CN:nanchang", name: "南昌", nameEn: "Nanchang", region: "江西省", regionEn: "Jiangxi", country: "中国", countryEn: "China", latitude: 28.67999229, longitude: 115.8799963, timezone: "Asia/Shanghai", aliases: ["南昌", "nanchang"], population: 2110675.5 },
  { id: "CN:jinan", name: "济南", nameEn: "Jinan", region: "山东省", regionEn: "Shandong", country: "中国", countryEn: "China", latitude: 36.67498232, longitude: 116.9950187, timezone: "Asia/Shanghai", aliases: ["济南", "濟南", "jinan"], population: 2433633 },
  { id: "CN:zhengzhou", name: "郑州", nameEn: "Zhengzhou", region: "河南省", regionEn: "Henan", country: "中国", countryEn: "China", latitude: 34.75499615, longitude: 113.6650927, timezone: "Asia/Shanghai", aliases: ["郑州", "鄭州", "zhengzhou"], population: 2325062.5 },
  { id: "CN:wuhan", name: "武汉", nameEn: "Wuhan", region: "湖北省", regionEn: "Hubei", country: "中国", countryEn: "China", latitude: 30.58003135, longitude: 114.270017, timezone: "Asia/Shanghai", aliases: ["武汉", "武漢", "wuhan"], population: 5713603 },
  { id: "CN:changsha", name: "长沙", nameEn: "Changsha", region: "湖南省", regionEn: "Hunan", country: "中国", countryEn: "China", latitude: 28.19996991, longitude: 112.969993, timezone: "Asia/Shanghai", aliases: ["长沙", "長沙", "changsha"], population: 2338969 },
  { id: "CN:guangzhou", name: "广州", nameEn: "Guangzhou", region: "广东省", regionEn: "Guangdong", country: "中国", countryEn: "China", latitude: 23.1449813, longitude: 113.3250101, timezone: "Asia/Shanghai", aliases: ["广州", "廣州", "guangzhou", "canton"], population: 5990912.5 },
  { id: "CN:shenzhen", name: "深圳", nameEn: "Shenzhen", region: "广东省", regionEn: "Guangdong", country: "中国", countryEn: "China", latitude: 22.55237051, longitude: 114.1221231, timezone: "Asia/Shanghai", aliases: ["深圳", "shenzhen"], population: 4291796 },
  { id: "CN:nanning", name: "南宁", nameEn: "Nanning", region: "广西壮族自治区", regionEn: "Guangxi", country: "中国", countryEn: "China", latitude: 22.81998822, longitude: 108.3200443, timezone: "Asia/Shanghai", aliases: ["南宁", "南寧", "nanning"], population: 1485394 },
  { id: "CN:haikou", name: "海口", nameEn: "Haikou", region: "海南省", regionEn: "Hainan", country: "中国", countryEn: "China", latitude: 20.05000226, longitude: 110.3200256, timezone: "Asia/Shanghai", aliases: ["海口", "haikou"], population: 1606808.5 },
  { id: "CN:chengdu", name: "成都", nameEn: "Chengdu", region: "四川省", regionEn: "Sichuan", country: "中国", countryEn: "China", latitude: 30.67000002, longitude: 104.0700195, timezone: "Asia/Shanghai", aliases: ["成都", "chengdu"], population: 4036718.5 },
  { id: "CN:guiyang", name: "贵阳", nameEn: "Guiyang", region: "贵州省", regionEn: "Guizhou", country: "中国", countryEn: "China", latitude: 26.58004295, longitude: 106.7200386, timezone: "Asia/Shanghai", aliases: ["贵阳", "貴陽", "guiyang"], population: 2416816.5 },
  { id: "CN:kunming", name: "昆明", nameEn: "Kunming", region: "云南省", regionEn: "Yunnan", country: "中国", countryEn: "China", latitude: 25.06998008, longitude: 102.6799751, timezone: "Asia/Shanghai", aliases: ["昆明", "kunming"], population: 1977337 },
  { id: "CN:lhasa", name: "拉萨", nameEn: "Lhasa", region: "西藏自治区", regionEn: "Tibet", country: "中国", countryEn: "China", latitude: 29.64502382, longitude: 91.10001013, timezone: "Asia/Shanghai", aliases: ["拉萨", "拉薩", "lhasa"], population: 169160 },
  { id: "CN:xian", name: "西安", nameEn: "Xi'an", region: "陕西省", regionEn: "Shaanxi", country: "中国", countryEn: "China", latitude: 34.27502545, longitude: 108.8949963, timezone: "Asia/Shanghai", aliases: ["西安", "xian", "xi'an", "xi’an"], population: 3617406 },
  { id: "CN:lanzhou", name: "兰州", nameEn: "Lanzhou", region: "甘肃省", regionEn: "Gansu", country: "中国", countryEn: "China", latitude: 36.05602785, longitude: 103.7920003, timezone: "Asia/Shanghai", aliases: ["兰州", "蘭州", "lanzhou"], population: 2282609 },
  { id: "CN:xining", name: "西宁", nameEn: "Xining", region: "青海省", regionEn: "Qinghai", country: "中国", countryEn: "China", latitude: 36.6199986, longitude: 101.7700048, timezone: "Asia/Shanghai", aliases: ["西宁", "西寧", "xining"], population: 907765.5 },
  { id: "CN:yinchuan", name: "银川", nameEn: "Yinchuan", region: "宁夏回族自治区", regionEn: "Ningxia", country: "中国", countryEn: "China", latitude: 38.46797365, longitude: 106.2730375, timezone: "Asia/Shanghai", aliases: ["银川", "銀川", "yinchuan"], population: 657614 },
  { id: "CN:urumqi", name: "乌鲁木齐", nameEn: "Urumqi", region: "新疆维吾尔自治区", regionEn: "Xinjiang", country: "中国", countryEn: "China", latitude: 43.80501223, longitude: 87.57500565, timezone: "Asia/Shanghai", aliases: ["乌鲁木齐", "烏魯木齊", "urumqi"], population: 1829612.5 },
  { id: "CN:qingdao", name: "青岛", nameEn: "Qingdao", region: "山东省", regionEn: "Shandong", country: "中国", countryEn: "China", latitude: 36.08997927, longitude: 120.3300089, timezone: "Asia/Shanghai", aliases: ["青岛", "青島", "qingdao"], population: 2254122.5 },
  { id: "CN:dalian", name: "大连", nameEn: "Dalian", region: "辽宁省", regionEn: "Liaoning", country: "中国", countryEn: "China", latitude: 38.92283839, longitude: 121.6298308, timezone: "Asia/Shanghai", aliases: ["大连", "大連", "dalian"], population: 2601153.5 },
  { id: "CN:xiamen", name: "厦门", nameEn: "Xiamen", region: "福建省", regionEn: "Fujian", country: "中国", countryEn: "China", latitude: 24.44999208, longitude: 118.080017, timezone: "Asia/Shanghai", aliases: ["厦门", "廈門", "xiamen"], population: 1548668.5 },
  { id: "CN:suzhou-jiangsu", name: "苏州", nameEn: "Suzhou", region: "江苏省", regionEn: "Jiangsu", country: "中国", countryEn: "China", latitude: 31.30047833, longitude: 120.620017, timezone: "Asia/Shanghai", aliases: ["苏州", "蘇州", "suzhou", "suzhou jiangsu"], population: 1496545.5 },
  { id: "CN:ningbo", name: "宁波", nameEn: "Ningbo", region: "浙江省", regionEn: "Zhejiang", country: "中国", countryEn: "China", latitude: 29.87997072, longitude: 121.5500378, timezone: "Asia/Shanghai", aliases: ["宁波", "寧波", "ningbo"], population: 1321433.5 },
  { id: "HK:hong-kong", name: "香港", nameEn: "Hong Kong", region: "香港特别行政区", regionEn: "Hong Kong", country: "中国香港", countryEn: "Hong Kong S.A.R.", latitude: 22.3049809, longitude: 114.1850093, timezone: "Asia/Hong_Kong", aliases: ["香港", "hong kong", "hongkong"], population: 5878789.5 },
  { id: "MO:macau", name: "澳门", nameEn: "Macau", region: "澳门特别行政区", regionEn: "Macau", country: "中国澳门", countryEn: "Macau S.A.R.", latitude: 22.20299746, longitude: 113.5450484, timezone: "Asia/Macau", aliases: ["澳门", "澳門", "macau", "macao"], population: 568700 },
  { id: "TW:taipei", name: "台北", nameEn: "Taipei", region: "台北市", regionEn: "Taipei City", country: "中国台湾", countryEn: "Taiwan", latitude: 25.03583333, longitude: 121.5683333, timezone: "Asia/Taipei", aliases: ["台北", "臺北", "taipei"], population: 4759522.5 },
]

export const CHINESE_CITY_ALIASES = CURATED_LOCATIONS

export function normalizeLocationQuery(value: string) {
  return value.normalize("NFKD").replace(/[\u0300-\u036f]/g, "").trim().toLocaleLowerCase().replace(/\s+/g, " ").slice(0, MAX_QUERY_LENGTH)
}

function curatedResult(location: CuratedLocation, locale: Locale): LocationResult {
  if (locale === "zh") {
    const { id, name, region, country, latitude, longitude, timezone } = location
    return { id, name, region, country, latitude, longitude, timezone }
  }
  return { id: location.id, name: location.nameEn, region: location.regionEn, country: location.countryEn, latitude: location.latitude, longitude: location.longitude, timezone: location.timezone }
}

function datasetResult(record: CityRecord): LocationResult {
  return {
    id: `${record.iso2}:${record.city}:${record.province || record.state_ansi || ""}:${record.lat}:${record.lng}`,
    name: record.city,
    region: record.province || record.state_ansi || "",
    country: record.country,
    latitude: record.lat,
    longitude: record.lng,
    timezone: record.timezone,
  }
}

const CURATED_INDEX: IndexedLocation[] = CURATED_LOCATIONS.map((location) => ({
  resultEn: curatedResult(location, "en"),
  resultZh: curatedResult(location, "zh"),
  normalizedText: normalizeLocationQuery([location.name, location.nameEn, location.region, location.regionEn, location.country, location.countryEn, ...location.aliases].join(" ")),
  population: location.population,
  curated: true,
}))

const DATASET_INDEX: IndexedLocation[] = cityMapping.map((record) => ({
  resultEn: datasetResult(record),
  normalizedText: normalizeLocationQuery([record.city, record.city_ascii, record.province, record.state_ansi, record.country, record.iso2, record.iso3].filter(Boolean).join(" ")),
  population: record.pop || 0,
  curated: false,
}))

export const NORMALIZED_LOCATION_INDEX: IndexedLocation[] = [...CURATED_INDEX, ...DATASET_INDEX]

function resultForLocale(entry: IndexedLocation, locale: Locale) {
  return locale === "zh" && entry.resultZh ? entry.resultZh : entry.resultEn
}

function dedupeKey(result: LocationResult) {
  return `${result.latitude.toFixed(5)}:${result.longitude.toFixed(5)}`
}

export function searchLocations(query: string, locale: Locale): LocationResult[] {
  const normalizedQuery = normalizeLocationQuery(query)
  if (normalizedQuery.length < 2) return []
  const terms = normalizedQuery.split(" ")
  const matches = NORMALIZED_LOCATION_INDEX
    .filter((entry) => terms.every((term) => entry.normalizedText.includes(term)))
    .toSorted((left, right) => Number(right.curated) - Number(left.curated) || right.population - left.population)

  const deduped = new Map<string, LocationResult>()
  for (const entry of matches) {
    const result = resultForLocale(entry, locale)
    const key = dedupeKey(result)
    if (!deduped.has(key)) deduped.set(key, result)
    if (deduped.size === 8) break
  }
  return Array.from(deduped.values()).slice(0, 8)
}

export function isValidCoordinates(latitude: number, longitude: number) {
  return Number.isFinite(latitude) && Number.isFinite(longitude)
    && latitude >= -90 && latitude <= 90
    && longitude >= -180 && longitude <= 180
}

function toRadians(value: number) {
  return value * Math.PI / 180
}

export function haversineDistanceKm(latitudeA: number, longitudeA: number, latitudeB: number, longitudeB: number) {
  const earthRadiusKm = 6371.0088
  const latitudeDelta = toRadians(latitudeB - latitudeA)
  const longitudeDelta = toRadians(longitudeB - longitudeA)
  const startLatitude = toRadians(latitudeA)
  const endLatitude = toRadians(latitudeB)
  const haversine = Math.sin(latitudeDelta / 2) ** 2
    + Math.cos(startLatitude) * Math.cos(endLatitude) * Math.sin(longitudeDelta / 2) ** 2
  return earthRadiusKm * 2 * Math.atan2(Math.sqrt(haversine), Math.sqrt(1 - haversine))
}

export function findNearestLocation(latitude: number, longitude: number, locale: Locale): { result: LocationResult; distanceKm: number } | null {
  if (!isValidCoordinates(latitude, longitude)) return null
  let nearestEntry: IndexedLocation | null = null
  let distanceKm = Number.POSITIVE_INFINITY
  for (const entry of NORMALIZED_LOCATION_INDEX) {
    const result = entry.resultEn
    const candidateDistance = haversineDistanceKm(latitude, longitude, result.latitude, result.longitude)
    if (candidateDistance < distanceKm) {
      nearestEntry = entry
      distanceKm = candidateDistance
    }
  }
  if (!nearestEntry || distanceKm > MAX_NEAREST_DISTANCE_KM) return null
  return { result: resultForLocale(nearestEntry, locale), distanceKm: Math.round(distanceKm * 10) / 10 }
}
