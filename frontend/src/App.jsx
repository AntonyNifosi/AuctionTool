import { Routes, Route } from 'react-router-dom'
import Sidebar from './components/Layout/Sidebar'
import ItemsPage from './pages/ItemsPage'
import ProfitsPage from './pages/ProfitsPage'
import PetsPage from './pages/PetsPage'
import CollectionPage from './pages/CollectionPage'
import { RealmProvider } from './context/RealmContext'

function App() {
    return (
        <RealmProvider>
            <div className="app">
                <Sidebar />
                <main className="main-content">
                    <Routes>
                        <Route path="/" element={<ItemsPage />} />
                        <Route path="/items" element={<ItemsPage />} />
                        <Route path="/profits" element={<ProfitsPage />} />
                        <Route path="/pets" element={<PetsPage />} />
                        <Route path="/collection" element={<CollectionPage />} />
                    </Routes>
                </main>
            </div>
        </RealmProvider>
    )
}

export default App
