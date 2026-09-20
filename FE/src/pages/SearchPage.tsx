import { ChevronRight, Info, LogIn, Search, X } from 'lucide-react';
import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';
import { getAutocomplete, getPopularKeywords, searchPlaces, type SearchResult, type SearchType } from '../api/search';
import spotPlaceholder from '../assets/placeholder/spot.png';
import workPlaceholder from '../assets/placeholder/work.png';
import { BottomNav } from '../components/BottomNav';
import { PlaceholderImage } from '../components/PlaceholderImage';
import { Skeleton } from '../components/Skeleton';
import { useRecentSearches } from '../hooks/useRecentSearches';
import { useAuthStore } from '../store/useAuthStore';

const FILTERS: { type?: SearchType; labelKey: string }[] = [
    { type: undefined, labelKey: 'searchPage.filters.all' },
    { type: 'DRAMA', labelKey: 'searchPage.filters.drama' },
    { type: 'MOVIE', labelKey: 'searchPage.filters.movie' },
];

// 촬영지 탭 안에서 이름/주소 중 어디에 검색어가 매칭됐는지로 한 번 더 거른다.
// BE가 아직 이름만 검색해서(주소 검색 이슈 등록 예정), '주소명'을 골라도 지금은
// "이름으로 찾아진 결과 중 주소에도 검색어가 포함된 것"만 보인다 — BE가 주소까지
// 검색하게 되면 그때부터 이 필터가 온전히 동작한다.
type PlaceFilter = 'all' | 'name' | 'address';
const PLACE_FILTERS: { type: PlaceFilter; labelKey: string }[] = [
    { type: 'all', labelKey: 'searchPage.placeFilters.all' },
    { type: 'name', labelKey: 'searchPage.placeFilters.name' },
    { type: 'address', labelKey: 'searchPage.placeFilters.address' },
];

// 결과가 많아도 명소·작품 목록 둘 다 이 개수까지만 보여준다("더보기" 없이 그냥 자름).
const RESULT_LIMIT = 10;

type ResultTab = 'place' | 'work';
const RESULT_TABS: { type: ResultTab; labelKey: string }[] = [
    { type: 'place', labelKey: 'searchPage.tabs.place' },
    { type: 'work', labelKey: 'searchPage.tabs.work' },
];

export function SearchPage() {
    const { t } = useTranslation();
    const member = useAuthStore(state => state.member);
    const isLoading = useAuthStore(state => state.isLoading);
    const { recentSearches, addRecentSearch, clearRecentSearches } = useRecentSearches();

    const [query, setQuery] = useState('');
    const [submittedQuery, setSubmittedQuery] = useState('');
    const [resultTab, setResultTab] = useState<ResultTab>('place');
    const [placeFilter, setPlaceFilter] = useState<PlaceFilter>('all');
    const [type, setType] = useState<SearchType | undefined>(undefined);
    const [suggestions, setSuggestions] = useState<string[]>([]);
    const [popularKeywords, setPopularKeywords] = useState<string[]>([]);
    const [showPopularInfo, setShowPopularInfo] = useState(false);
    // undefined: 검색 중, { places: [], works: [] }: 검색 끝났는데 결과 없음
    const [results, setResults] = useState<SearchResult | undefined>(undefined);

    useEffect(() => {
        getPopularKeywords()
            .then(setPopularKeywords)
            .catch(() => setPopularKeywords([]));
    }, []);

    useEffect(() => {
        const trimmed = query.trim();
        if (submittedQuery || !trimmed) {
            setSuggestions([]);
            return;
        }
        const timer = setTimeout(() => {
            getAutocomplete(trimmed)
                .then(setSuggestions)
                .catch(() => setSuggestions([]));
        }, 300);
        return () => clearTimeout(timer);
    }, [query, submittedQuery]);

    // 필터(전체/드라마/영화)는 API를 다시 안 부르고, 이미 받아온 작품 목록을 화면에서만 걸러서 보여준다.
    // (검색 API에 type을 넘기면 BE가 명소 결과를 아예 비워버려서, "명소에서 검색됨" 섹션까지 같이 사라지는 문제가 있었다.)
    function runSearch(keyword: string) {
        setResults(undefined);
        searchPlaces(keyword)
            .then(setResults)
            .catch(() => setResults({ places: [], works: [] }));
    }

    function handleSubmit(keyword: string) {
        const trimmed = keyword.trim();
        if (!trimmed) {
            return;
        }
        setQuery(trimmed);
        setSubmittedQuery(trimmed);
        setSuggestions([]);
        addRecentSearch(trimmed);
        runSearch(trimmed);
    }

    function handleFilterChange(nextType: SearchType | undefined) {
        setType(nextType);
    }

    const filteredWorks = results
        ? type
            ? results.works.filter(work => work.category === type)
            : results.works
        : undefined;

    const normalizedSubmittedQuery = submittedQuery.trim().toLowerCase();
    const filteredPlaces = results
        ? results.places.filter(place => {
              if (placeFilter === 'name') {
                  return place.name.toLowerCase().includes(normalizedSubmittedQuery);
              }
              if (placeFilter === 'address') {
                  return place.address.toLowerCase().includes(normalizedSubmittedQuery);
              }
              return true;
          })
        : undefined;

    function handleClear() {
        setQuery('');
        setSubmittedQuery('');
        setResultTab('place');
        setPlaceFilter('all');
        setType(undefined);
        setSuggestions([]);
        setResults(undefined);
    }

    return (
        <main className="flex min-h-dvh flex-col gap-6 pb-24">
            <header className="flex items-center justify-between px-4 pt-4">
                <Link to="/" className="font-brand text-2xl font-bold text-primary">
                    여운
                </Link>
                {!isLoading && !member && (
                    <Link to="/login" aria-label="로그인">
                        <LogIn size={22} className="text-ink" />
                    </Link>
                )}
            </header>

            <div className="px-4">
                {submittedQuery ? (
                    <h1 className="text-xl font-bold text-ink">
                        {t('searchPage.resultsTitle', { query: submittedQuery })}
                    </h1>
                ) : (
                    <h1 className="whitespace-pre-line text-xl font-bold text-ink">{t('searchPage.title')}</h1>
                )}
            </div>

            <div className="px-4 mb-6">
                <div className="flex items-center gap-2 border-b-2 border-primary p-4">
                    <input
                        type="text"
                        value={query}
                        onChange={event => setQuery(event.target.value)}
                        onKeyDown={event => event.key === 'Enter' && handleSubmit(query)}
                        placeholder={t('searchPage.placeholder')}
                        className="flex-1 text-sm text-ink placeholder:text-ink-secondary outline-none"
                    />
                    {query && (
                        <button type="button" onClick={handleClear} aria-label={t('searchPage.clearButton')}>
                            <X size={18} className="text-ink-tertiary" />
                        </button>
                    )}
                    <button type="button" onClick={() => handleSubmit(query)} aria-label={t('searchPage.searchButton')}>
                        <Search size={20} className="text-primary" />
                    </button>
                </div>

                {!submittedQuery && suggestions.length > 0 && (
                    <div className="mt-2 flex flex-col">
                        {suggestions.map(suggestion => (
                            <button
                                key={suggestion}
                                type="button"
                                onClick={() => handleSubmit(suggestion)}
                                className="flex items-center gap-2 py-2 text-left text-sm text-ink"
                            >
                                <Search size={14} className="text-ink-tertiary" />
                                {suggestion}
                            </button>
                        ))}
                    </div>
                )}
            </div>

            {submittedQuery ? (
                <>
                    <div className="flex gap-6 border-b border-divider px-4">
                        {RESULT_TABS.map(tab => (
                            <button
                                key={tab.type}
                                type="button"
                                onClick={() => setResultTab(tab.type)}
                                className={`pb-2 text-sm ${
                                    resultTab === tab.type
                                        ? 'border-b-2 border-primary font-bold text-ink'
                                        : 'text-ink-tertiary'
                                }`}
                            >
                                {t(tab.labelKey)}
                            </button>
                        ))}
                    </div>

                    {resultTab === 'work' && (
                        <section className="px-4">
                            <div className="mb-4 flex gap-2">
                                {FILTERS.map(filter => {
                                    const active = filter.type === type;
                                    return (
                                        <button
                                            key={filter.labelKey}
                                            type="button"
                                            onClick={() => handleFilterChange(filter.type)}
                                            className={`rounded-full border px-3 py-1.5 text-xs ${
                                                active
                                                    ? 'border-primary font-bold text-primary'
                                                    : 'border-ink-tertiary text-ink-secondary'
                                            }`}
                                        >
                                            {t(filter.labelKey)}
                                        </button>
                                    );
                                })}
                            </div>

                            {filteredWorks === undefined ? (
                                <ResultSkeleton />
                            ) : filteredWorks.length > 0 ? (
                                <div className="flex flex-col gap-4">
                                    {filteredWorks.slice(0, RESULT_LIMIT).map(work => (
                                        <ResultRow
                                            key={work.id}
                                            to={`/works/${work.id}`}
                                            thumbnail={work.poster_url}
                                            thumbnailPlaceholder={workPlaceholder}
                                            title={work.title}
                                            subtitle={
                                                work.category === 'DRAMA'
                                                    ? t('searchPage.filters.drama')
                                                    : t('searchPage.filters.movie')
                                            }
                                        />
                                    ))}
                                </div>
                            ) : (
                                <p className="text-sm text-ink-tertiary">{t('searchPage.noResults')}</p>
                            )}
                        </section>
                    )}

                    {resultTab === 'place' && (
                        <section className="px-4">
                            <div className="mb-4 flex gap-2">
                                {PLACE_FILTERS.map(filter => {
                                    const active = filter.type === placeFilter;
                                    return (
                                        <button
                                            key={filter.type}
                                            type="button"
                                            onClick={() => setPlaceFilter(filter.type)}
                                            className={`rounded-full border px-3 py-1.5 text-xs ${
                                                active
                                                    ? 'border-primary font-bold text-primary'
                                                    : 'border-ink-tertiary text-ink-secondary'
                                            }`}
                                        >
                                            {t(filter.labelKey)}
                                        </button>
                                    );
                                })}
                            </div>

                            {filteredPlaces === undefined ? (
                                <ResultSkeleton />
                            ) : filteredPlaces.length > 0 ? (
                                <div className="flex flex-col gap-4">
                                    {filteredPlaces.slice(0, RESULT_LIMIT).map(place => (
                                        <ResultRow
                                            key={place.id}
                                            to={`/spots/${place.id}`}
                                            thumbnail={place.photo_url}
                                            thumbnailPlaceholder={spotPlaceholder}
                                            title={place.name}
                                            subtitle={place.address}
                                        />
                                    ))}
                                </div>
                            ) : (
                                <p className="text-sm text-ink-tertiary">{t('searchPage.noResults')}</p>
                            )}
                        </section>
                    )}
                </>
            ) : (
                <>
                    {recentSearches.length > 0 && (
                        <section className="px-4">
                            <div className="mb-4 flex items-center justify-between">
                                <h2 className="text-base font-bold text-ink">{t('searchPage.recentSearchesTitle')}</h2>
                                <button
                                    type="button"
                                    onClick={clearRecentSearches}
                                    className="text-sm text-ink-tertiary"
                                >
                                    {t('searchPage.recentSearchesClear')}
                                </button>
                            </div>
                            <div className="flex flex-wrap gap-3">
                                {recentSearches.map(keyword => (
                                    <button
                                        key={keyword}
                                        type="button"
                                        onClick={() => handleSubmit(keyword)}
                                        className="rounded-full border border-ink-tertiary px-3 py-2 text-sm text-ink-secondary"
                                    >
                                        #{keyword}
                                    </button>
                                ))}
                            </div>
                        </section>
                    )}

                    <section className="px-4 mt-6">
                        <div className="mb-4 flex items-center gap-1">
                            <h2 className="text-base font-bold text-ink">{t('searchPage.popularKeywordsTitle')}</h2>
                            <button
                                type="button"
                                onClick={() => setShowPopularInfo(prev => !prev)}
                                aria-label={t('searchPage.popularKeywordsInfo')}
                            >
                                <Info size={14} className="text-ink-tertiary" />
                            </button>
                            {showPopularInfo && (
                                <p className="whitespace-nowrap text-xs text-ink-tertiary">{t('searchPage.popularKeywordsInfo')}</p>
                            )}
                        </div>

                        <div className="flex flex-wrap gap-3">
                            {popularKeywords.map(keyword => (
                                <button
                                    key={keyword}
                                    type="button"
                                    onClick={() => handleSubmit(keyword)}
                                    className="rounded-full border border-ink-tertiary px-3 py-2 text-sm text-ink-secondary"
                                >
                                    #{keyword}
                                </button>
                            ))}
                        </div>
                    </section>
                </>
            )}

            <BottomNav />
        </main>
    );
}

type ResultRowProps = {
    thumbnail: string;
    thumbnailPlaceholder: string;
    title: string;
    subtitle: string;
    to?: string;
};

function ResultRow({ thumbnail, thumbnailPlaceholder, title, subtitle, to }: ResultRowProps) {
    const content = (
        <>
            <PlaceholderImage
                src={thumbnail}
                placeholder={thumbnailPlaceholder}
                alt=""
                className="h-[74px] w-[75px] rounded-2xl"
            />
            <div className="flex-1">
                <p className="text-xs text-ink">{title}</p>
                <p className="text-[11px] text-ink-secondary">{subtitle}</p>
            </div>
            <ChevronRight size={20} className="text-ink-tertiary" />
        </>
    );

    if (to) {
        return (
            <Link to={to} className="flex items-center gap-3">
                {content}
            </Link>
        );
    }
    return <div className="flex items-center gap-3">{content}</div>;
}

function ResultSkeleton() {
    return (
        <div className="flex flex-col gap-4">
            {[0, 1].map(i => (
                <div key={i} className="flex items-center gap-3">
                    <Skeleton className="h-[74px] w-[75px] rounded-2xl" />
                    <div className="flex flex-1 flex-col gap-2">
                        <Skeleton className="h-3 w-1/2 rounded-sm" />
                        <Skeleton className="h-3 w-1/3 rounded-sm" />
                    </div>
                </div>
            ))}
        </div>
    );
}
