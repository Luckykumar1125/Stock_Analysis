import React, { useState, useMemo } from 'react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Label } from "@/components/ui/label";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { 
    Select, 
    SelectContent, 
    SelectItem, 
    SelectTrigger, 
    SelectValue 
} from "@/components/ui/select";

import { toast } from "sonner"; 
import { ArrowUpDown, Loader2, ArrowUp, ArrowDown } from 'lucide-react';
import { useTable, useSortBy, Column, TableOptions } from 'react-table'; 
import { cn } from "@/lib/utils"; 

// ----------------------------------------------------------------------
// --- CONFIGURATION: SECTOR LIST ---
// ----------------------------------------------------------------------

const INDIAN_SECTORS = [
    "Banking & Finance",
    "Information Technology (IT)",
    "Pharmaceuticals & Healthcare",
    "Automobile & Auto Ancillaries",
    "Oil, Gas & Energy",
    "FMCG (Fast Moving Consumer Goods)",
    "Infrastructure & Cement",
    "Telecommunications",
    "Metals & Mining",
    "Chemicals",
    "Real Estate",
];

// ----------------------------------------------------------------------
// --- TYPE DEFINITIONS & UTILITY FUNCTIONS (Unchanged) ---
// ----------------------------------------------------------------------

interface StockData {
  ticker: string;
  company: string;
  price: number | null;
  change: number | null;
  change_percent: number | null;
  market_cap: number | null;
  '52_week_high': number | null;
  '52_week_low': number | null;
  volume: number | null;
  sector: string;
  industry: string;
  error?: string;
}

interface ScreenerResults {
  status: 'success' | 'failed' | 'error';
  sector: string;
  total_stocks: number;
  stocks: StockData[];
  message?: string;
}

const formatNumber = (num: number | null | undefined): string => {
  if (num === null || num === undefined) return 'N/A';
  if (num >= 1e12) return (num / 1e12).toFixed(2) + ' Trillion';
  if (num >= 1e9) return (num / 1e9).toFixed(2) + ' Billion';
  if (num >= 1e6) return (num / 1e6).toFixed(2) + ' Million';
  return num.toLocaleString();
};

const ChangeCell: React.FC<{ value: number | null }> = ({ value }) => {
  if (value === null) return <span className="text-gray-500">N/A</span>;
  const isPositive = value > 0;
  const isNeutral = value === 0;
  
  let colorClass = 'text-gray-500';
  let Icon = null;

  if (isPositive) {
    colorClass = 'text-green-600';
    Icon = ArrowUp;
  } else if (!isNeutral) {
    colorClass = 'text-red-600';
    Icon = ArrowDown;
  }

  return (
    <div className={cn("flex items-center space-x-1", colorClass)}>
      {Icon && <Icon className="h-3 w-3" />}
      <span>{value !== null ? value.toFixed(2) : 'N/A'}%</span>
    </div>
  );
};

// --- API CALL (Simulated Fetch - REPLACE WITH ACTUAL ENDPOINT) ---

const BACKEND_URL = 'http://127.0.0.1:8000';

const fetchStocks = async (sector: string): Promise<ScreenerResults> => {

    // --- START: Simulation (Remove this block for production) ---

    console.log(`Fetching data for sector: ${sector}`);

    await new Promise(resolve => setTimeout(resolve, 2000)); // Simulate API delay

      try {

        const response = await fetch(`${BACKEND_URL}/get-sector-stocks`, {

            method: 'POST',

            headers: { 'Content-Type': 'application/json' },

            body: JSON.stringify({ sector: sector }),

        });

        if (!response.ok) {

            throw new Error(`HTTP error! status: ${response.status}`);

        }

        return await response.json() as ScreenerResults;

    } catch (e) {

        console.error("API Fetch Error:", e);

        return { status: 'error', sector: sector, total_stocks: 0, stocks: [], message: 'Network or server error.' };

    }

    

};

// --- TABLE COMPONENT (Unchanged) ---

const StockDataDisplay: React.FC<{ data: StockData[] }> = ({ data }) => {
  const columns: Array<Column<StockData>> = useMemo(
    () => [
      {
        Header: 'Company',
        accessor: 'company',
        Cell: ({ row }) => (
            <div className="flex flex-col space-y-0">
                <p className="font-semibold">{row.original.company}</p>
                <p className="text-xs text-gray-500">{row.original.ticker}</p>
            </div>
        )
      },
      {
        Header: 'Sector',
        accessor: 'sector',
        Cell: ({ value }) => <Badge variant="secondary">{value}</Badge>,
        disableSortBy: true,
      },
      {
        Header: 'Price (₹)',
        accessor: 'price',
        Cell: ({ value }) => (value !== null ? `₹ ${value.toFixed(2)}` : 'N/A'),
      },
      {
        Header: 'Change (%)',
        accessor: 'change_percent',
        Cell: ({ value }) => <ChangeCell value={value} />,
      },
      {
        Header: 'Mkt Cap',
        accessor: 'market_cap',
        Cell: ({ value }) => <p className='text-sm'>{formatNumber(value)}</p>,
      },
      {
        Header: '52W High',
        accessor: '52_week_high',
        Cell: ({ value }) => (value !== null ? `₹ ${value.toFixed(2)}` : 'N/A'),
      },
    ],
    []
  );

  const tableInstance = useTable(
    { columns, data, initialState: { sortBy: [{ id: 'market_cap', desc: true }] } } as TableOptions<StockData>,
    useSortBy
  );

  const {
    getTableProps,
    getTableBodyProps,
    headerGroups,
    rows,
    prepareRow,
  } = tableInstance;


  if (data.length === 0) {
    return (
      <div className="p-8 bg-gray-50 dark:bg-gray-900 rounded-lg text-center">
        <p className="text-gray-500">No stock data available for this sector.</p>
      </div>
    );
  }

  return (
    <div className="overflow-x-auto border rounded-lg">
      <Table {...getTableProps()}>
        <TableHeader>
          {headerGroups.map((headerGroup) => (
            <TableRow {...headerGroup.getHeaderGroupProps()}>
              {headerGroup.headers.map((column) => (
                <TableHead
                  {...column.getHeaderProps(column.getSortByToggleProps())}
                  className="cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800"
                >
                  <div className="flex items-center gap-1.5">
                    {column.render('Header')}
                    {column.canSort && (
                      column.isSorted ? (
                        column.isSortedDesc ? (
                          <ArrowDown className="h-3 w-3 text-primary" />
                        ) : (
                          <ArrowUp className="h-3 w-3 text-primary" />
                        )
                      ) : (
                        <ArrowUpDown className="ml-2 h-3 w-3 text-gray-400" />
                      )
                    )}
                  </div>
                </TableHead>
              ))}
            </TableRow>
          ))}
        </TableHeader>
        <TableBody {...getTableBodyProps()}>
          {rows.map((row) => {
            prepareRow(row);
            return (
              <TableRow {...row.getRowProps()}>
                {row.cells.map((cell) => {
                  return (
                    <TableCell {...cell.getCellProps()}>
                      {cell.render('Cell')}
                    </TableCell>
                  );
                })}
              </TableRow>
            );
          })}
        </TableBody>
      </Table>
    </div>
  );
};


// ----------------------------------------------------------------------
// --- MAIN COMPONENT ---
// ----------------------------------------------------------------------

interface StockScreenerProps {
  id: string;
  icon: string;
  title: string;
  description: string;
  action: string;
}

const StockScreener: React.FC<StockScreenerProps> = (cardProps) => {
  const [isOpen, setIsOpen] = useState(false);
  const [selectedSector, setSelectedSector] = useState<string | undefined>(undefined); 
  const [results, setResults] = useState<ScreenerResults | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  // Directly open the dialog
  const openDialog = () => {
    setIsOpen(true);
    setSelectedSector(undefined);
    setResults(null);
    setIsLoading(false);
  };

  const handleSearch = async () => {
    if (!selectedSector || !selectedSector.trim()) {
      toast.warning('Selection Required', { 
        description: 'Please select a sector from the dropdown.',
        duration: 3000,
      });
      return;
    }

    setIsLoading(true);
    setResults(null);

    try {
      const data = await fetchStocks(selectedSector); 
      setResults(data);

      if (data.status !== 'success') {
        toast.error('Search Failed', {
          description: data.message || 'Could not retrieve stocks for this sector.',
          duration: 5000,
        });
      } else {
        toast.success(`Found ${data.total_stocks} stocks for ${data.sector}`, { duration: 3000 });
      }

    } catch (error) {
      console.error(error);
      toast.error('API Error', {
        description: 'Failed to connect to the backend server.',
        duration: 5000,
      });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <>
      {/* GRID BUTTON: Directly opens dialog */}
      <Button
        onClick={openDialog}
        size="lg"
        className="bg-indigo-600 hover:bg-indigo-700 text-white shadow-lg transition-all duration-200"
      >
        <span className="text-xl mr-2">{cardProps.icon}</span>
        {cardProps.action}
      </Button>

      {/* MAIN DIALOG */}
      <Dialog open={isOpen} onOpenChange={setIsOpen}>
        <DialogContent className="sm:max-w-[72rem] max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-3xl">
              <span className="text-2xl">{cardProps.icon}</span>
              {cardProps.title}
            </DialogTitle>
            <DialogDescription>{cardProps.description}</DialogDescription>
          </DialogHeader>

          {/* Your Select + Search UI here */}
          <div className="p-4 bg-gray-800 dark:bg-gray-900 border border-gray-700 rounded-lg">
            <div className="flex gap-4 items-end">
              <div className="flex-1 space-y-2">
                <Label htmlFor="sector-select" className="font-bold text-base text-gray-100">Select Indian Stock Sector</Label>
                
                <Select onValueChange={setSelectedSector} value={selectedSector}>
                  <SelectTrigger
                    id="sector-select"
                    className="bg-gray-900 text-gray-100 focus:ring-indigo-500 focus:ring-2 focus:border-indigo-500"
                  >
                    <SelectValue placeholder="Choose a major sector..." />
                  </SelectTrigger>
                  <SelectContent className="bg-gray-900 text-gray-100 border border-gray-700 rounded-md">
                    {INDIAN_SECTORS.map(sector => (
                      <SelectItem
                        key={sector}
                        value={sector}
                        className="text-gray-100 hover:bg-indigo-600 hover:text-white"
                      >
                        {sector}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <Button
                onClick={handleSearch}
                disabled={isLoading || !selectedSector}
                className="min-w-[150px] h-10 bg-indigo-600 hover:bg-indigo-700 text-white transition-colors duration-200"
              >
                {isLoading ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Fetching via AI...
                  </>
                ) : (
                  'Search Stocks'
                )}
              </Button>
            </div>
          </div>

          {/* Results display */}
          {isLoading && (
            <div className="flex flex-col items-center justify-center min-h-[200px] py-10">
              <Loader2 className="h-10 w-10 text-indigo-500 animate-spin" />
              <p className="mt-4 text-gray-400">Finding top companies and fetching data...</p>
            </div>
          )}

          {results && !isLoading && (
            <StockDataDisplay data={results.stocks.filter(s => !s.error)} />
          )}

        </DialogContent>
      </Dialog>
    </>
  );
};


export default StockScreener;